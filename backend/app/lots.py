"""Lotes (Story 2.4, AD-3, AD-6, AD-12, AD-23, AD-26, AD-30).

Um módulo, como `catalog.py`: modelo, schemas, regra pura, serviço e rotas. Dois
níveis de serviço, separados de propósito (A3):

- `resolve_artwork_for_lot`: a única ponte entre a criação de lote e a AIC. Só a
  criação manual (`POST /api/lots`) a chama.
- `create_lot`: a regra de criação e o `INSERT`, sem rede e sem cliente HTTP. A
  criação manual e o seed (`app/seed.py`) chegam a ela por caminhos diferentes.

Este módulo não importa `app.main`: o seed o importa e roda sem `APP_ORIGIN` e sem
`JWT_SECRET`.
"""

import logging
import re
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime
from enum import StrEnum
from typing import Annotated

from fastapi import Depends, FastAPI, Response
from pydantic import (
    AfterValidator,
    AwareDatetime,
    BaseModel,
    BeforeValidator,
    ConfigDict,
    Field,
    StrictInt,
    StringConstraints,
)
from pydantic_core import PydanticCustomError
from sqlalchemy import (
    BigInteger,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Select,
    String,
    Text,
    false,
    func,
    select,
    true,
)
from sqlalchemy.orm import Mapped, Session, mapped_column
from sqlalchemy.sql.expression import CTE

from app.access import NO_STORE, AccessPolicy, api_route, require_auctioneer
from app.artic import IMAGE_ID_PATTERN, ArticClient, CatalogUnavailable
from app.catalog import (
    MAX_EXTERNAL_ID,
    ArtworkDetail,
    LookupStatus,
    get_artic_client,
    get_artwork,
    image_url_for,
)
from app.db import Base, get_session
from app.errors import (
    ARTWORK_NOT_ELIGIBLE,
    CATALOG_UNAVAILABLE,
    error_response,
    error_responses,
)
from app.money import MAX_CENTS, Cents
from app.users import User

# Mesmo logger do uvicorn, para a mensagem aparecer no log do contêiner.
logger = logging.getLogger("uvicorn.error")

# Estrutura do horário aceito pela API (D2). O offset é opcional aqui de propósito:
# sem ele o `AwareDatetime` devolve `timezone_aware`, o erro certo. Número, data sem
# hora e espaço no lugar do `T` caem em `datetime_format`.
API_DATETIME_PATTERN = re.compile(
    r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}(:\d{2}(\.\d{1,6})?)?(Z|[+-]\d{2}:\d{2})?"
)


def _api_datetime_input(value: object) -> object:
    """Aceita `datetime` (chamada Python, como o seed) ou uma string ISO 8601 de
    estrutura reconhecida. O Pydantic aceitaria número como timestamp Unix."""
    if isinstance(value, datetime):
        return value
    if isinstance(value, str) and API_DATETIME_PATTERN.fullmatch(value):
        return value
    raise PydanticCustomError(
        "datetime_format", "Use uma data e hora ISO 8601 com fuso horário."
    )


def _api_datetime_normalizable(value: datetime) -> datetime:
    """Um horário só entra se couber em UTC: `9999-12-31T23:00:00-05:00` é válido na
    estrutura, mas passa de 9999-12-31 em UTC e `astimezone(UTC)` lançaria
    `OverflowError` mais tarde (500, depois de chamar a AIC). O mesmo vale para o
    extremo mínimo com offset positivo. A invariante é garantida aqui, na entrada."""
    try:
        value.astimezone(UTC)
    except OverflowError:
        raise PydanticCustomError(
            "datetime_format", "Use uma data e hora ISO 8601 com fuso horário."
        ) from None
    return value


ApiDatetime = Annotated[
    AwareDatetime,
    BeforeValidator(_api_datetime_input),
    AfterValidator(_api_datetime_normalizable),
]
ExternalId = Annotated[StrictInt, Field(gt=0, le=MAX_EXTERNAL_ID)]


class LotTerms(BaseModel):
    """Termos do leiloeiro. O seed usa este mesmo modelo."""

    model_config = ConfigDict(extra="forbid")

    starting_bid_cents: Cents
    min_increment_cents: Cents
    starts_at: ApiDatetime | None = None
    ends_at: ApiDatetime


class CreateLotRequest(LotTerms):
    """Corpo do `POST /api/lots`: só o `external_id` e os termos. Nada da obra."""

    external_id: ExternalId


class ArtworkSnapshot(BaseModel):
    """Os 11 campos de P2: o `ArtworkDetail` da 2.3 sem `image_url`."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    external_id: ExternalId
    title: str | None
    artist_display: str | None
    date_display: str | None
    medium_display: str | None
    dimensions: str | None
    department_title: str | None
    artwork_type_title: str | None
    image_id: Annotated[str, StringConstraints(pattern=f"^{IMAGE_ID_PATTERN.pattern}$")]
    credit_line: str | None
    source_url: str


def snapshot_from_detail(detail: ArtworkDetail) -> ArtworkSnapshot:
    return ArtworkSnapshot(**detail.model_dump(exclude={"image_url"}))


class Lot(Base):
    """Espelha a migration `0003`; o esquema dos testes vem sempre dela."""

    __tablename__ = "lots"
    __table_args__ = (
        CheckConstraint(
            f"starting_bid_cents > 0 AND starting_bid_cents <= {MAX_CENTS}",
            name="starting_bid_range",
        ),
        CheckConstraint(
            f"min_increment_cents > 0 AND min_increment_cents <= {MAX_CENTS}",
            name="min_increment_range",
        ),
        CheckConstraint("ends_at > starts_at", name="ends_after_starts"),
        CheckConstraint("external_id > 0", name="external_id_positive"),
        CheckConstraint(
            "image_id ~ "
            "'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$'",
            name="image_id_format",
        ),
    )

    # Sem default no banco para `id` e `created_at`: a aplicação os fornece (o
    # `created_at` é o instante lido do PostgreSQL, AD-6).
    id: Mapped[uuid.UUID] = mapped_column(primary_key=True)
    auctioneer_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT"), index=True
    )
    external_id: Mapped[int]
    title: Mapped[str | None] = mapped_column(Text)
    artist_display: Mapped[str | None] = mapped_column(Text)
    date_display: Mapped[str | None] = mapped_column(Text)
    medium_display: Mapped[str | None] = mapped_column(Text)
    dimensions: Mapped[str | None] = mapped_column(Text)
    department_title: Mapped[str | None] = mapped_column(Text)
    artwork_type_title: Mapped[str | None] = mapped_column(Text)
    image_id: Mapped[str] = mapped_column(String(36))
    credit_line: Mapped[str | None] = mapped_column(Text)
    source_url: Mapped[str] = mapped_column(Text)
    starting_bid_cents: Mapped[int] = mapped_column(BigInteger)
    min_increment_cents: Mapped[int] = mapped_column(BigInteger)
    starts_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    ends_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    is_demo: Mapped[bool] = mapped_column(server_default=false())
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


# --- regra pura (AD-26): recebe `now`, nunca lê o relógio ---


class ScheduleViolation(StrEnum):
    ENDS_AT_NOT_AFTER_START = "ends_at_not_after_start"
    STARTS_AT_NOT_IN_FUTURE = "starts_at_not_in_future"


@dataclass(frozen=True)
class Schedule:
    starts_at: datetime  # UTC
    ends_at: datetime  # UTC


def ends_not_after_scheduled_start(
    starts_at: datetime | None, ends_at: datetime
) -> bool:
    """Pré-checagem que não depende de `now` (D5): só quando o início veio no corpo."""
    return starts_at is not None and ends_at <= starts_at


def resolve_schedule(
    starts_at: datetime | None, ends_at: datetime, now: datetime
) -> Schedule | ScheduleViolation:
    """Início ausente = `now`; início presente precisa ser `> now`; o fim precisa ser
    posterior ao início efetivo. A comparação é entre instantes: o offset de entrada
    não importa. Tudo sai em UTC."""
    if now.tzinfo is None:
        raise ValueError("now must be timezone-aware")
    if starts_at is None:
        start = now
    else:
        if starts_at <= now:
            return ScheduleViolation.STARTS_AT_NOT_IN_FUTURE
        start = starts_at
    if ends_at <= start:
        return ScheduleViolation.ENDS_AT_NOT_AFTER_START
    return Schedule(starts_at=start.astimezone(UTC), ends_at=ends_at.astimezone(UTC))


class LotPhase(StrEnum):
    """Fase temporal do lote (2.4 §7, Story 2.5 P2). Derivada, nunca persistida: fim
    temporal não é liquidação, que só nasce na 4.3 (P8)."""

    SCHEDULED = "scheduled"
    LIVE = "live"
    ENDED = "ended"


def lot_phase(starts_at: datetime, ends_at: datetime, now: datetime) -> LotPhase:
    """`now < starts_at` agendado; `starts_at <= now < ends_at` ao vivo; `now >=
    ends_at` encerrado. Compara instantes: o offset de cada argumento não importa."""
    if now.tzinfo is None:
        raise ValueError("now must be timezone-aware")
    if now < starts_at:
        return LotPhase.SCHEDULED
    if now < ends_at:
        return LotPhase.LIVE
    return LotPhase.ENDED


# --- serviço, nível externo (só a criação manual) ---


class ArtworkRefusal(StrEnum):
    """Motivo interno, só para log e testes (P6): o cliente recebe um código só."""

    NOT_FOUND = "NOT_FOUND"
    NOT_PUBLIC_DOMAIN = "NOT_PUBLIC_DOMAIN"
    NO_IMAGE = "NO_IMAGE"


_REFUSAL_BY_STATUS = {
    LookupStatus.NOT_FOUND: ArtworkRefusal.NOT_FOUND,
    LookupStatus.NOT_PUBLIC_DOMAIN: ArtworkRefusal.NOT_PUBLIC_DOMAIN,
    LookupStatus.NO_IMAGE: ArtworkRefusal.NO_IMAGE,
}


def resolve_artwork_for_lot(
    client: ArticClient, external_id: int
) -> ArtworkSnapshot | ArtworkRefusal:
    """Consulta a AIC (uma requisição) e devolve o snapshot autoritativo, ou o motivo
    da recusa. `CatalogUnavailable` atravessa: a rota a traduz em 503. Não toca no
    banco."""
    lookup = get_artwork(client, external_id)
    if lookup.status == LookupStatus.FOUND and lookup.artwork is not None:
        return snapshot_from_detail(lookup.artwork)
    return _REFUSAL_BY_STATUS.get(lookup.status, ArtworkRefusal.NOT_FOUND)


# --- serviço, nível de persistência (criação manual e seed) ---


def database_now(session: Session) -> datetime:
    """O instante do PostgreSQL (AD-6), em UTC. Um por operação."""
    return session.execute(select(func.clock_timestamp())).scalar_one().astimezone(UTC)


def create_lot(
    session: Session,
    *,
    snapshot: ArtworkSnapshot,
    terms: LotTerms,
    auctioneer_id: uuid.UUID,
    now: datetime,
    is_demo: bool = False,
) -> Lot | ScheduleViolation:
    """Aplica a regra de horário e grava o lote. Sem rede: não recebe cliente HTTP
    nem consulta o catálogo. Não faz commit: quem chama decide."""
    schedule = resolve_schedule(terms.starts_at, terms.ends_at, now)
    if isinstance(schedule, ScheduleViolation):
        return schedule
    lot = Lot(
        id=uuid.uuid4(),
        auctioneer_id=auctioneer_id,
        **snapshot.model_dump(),
        starting_bid_cents=terms.starting_bid_cents,
        min_increment_cents=terms.min_increment_cents,
        starts_at=schedule.starts_at,
        ends_at=schedule.ends_at,
        is_demo=is_demo,
        created_at=now,
    )
    session.add(lot)
    session.flush()
    return lot


# --- contratos HTTP ---


class LotResponse(BaseModel):
    id: uuid.UUID
    external_id: int
    title: str | None
    artist_display: str | None
    date_display: str | None
    medium_display: str | None
    dimensions: str | None
    department_title: str | None
    artwork_type_title: str | None
    credit_line: str | None
    source_url: str
    image_id: str
    image_url: str
    starting_bid_cents: int
    min_increment_cents: int
    starts_at: datetime
    ends_at: datetime
    created_at: datetime


class MyLotsResponse(BaseModel):
    items: list[LotResponse]


def lot_response(lot: Lot) -> LotResponse:
    return LotResponse(
        id=lot.id,
        external_id=lot.external_id,
        title=lot.title,
        artist_display=lot.artist_display,
        date_display=lot.date_display,
        medium_display=lot.medium_display,
        dimensions=lot.dimensions,
        department_title=lot.department_title,
        artwork_type_title=lot.artwork_type_title,
        credit_line=lot.credit_line,
        source_url=lot.source_url,
        image_id=lot.image_id,
        image_url=image_url_for(lot.image_id),
        starting_bid_cents=lot.starting_bid_cents,
        min_increment_cents=lot.min_increment_cents,
        starts_at=lot.starts_at.astimezone(UTC),
        ends_at=lot.ends_at.astimezone(UTC),
        created_at=lot.created_at.astimezone(UTC),
    )


# --- leituras públicas (Story 2.5): DTOs próprios, separados do `LotResponse` ---


class PublicLotSummary(BaseModel):
    """Item da vitrine. Sem `auctioneer_id`, `is_demo`, `created_at` nem `image_id`."""

    id: uuid.UUID
    title: str | None
    artist_display: str | None
    date_display: str | None
    image_url: str
    starting_bid_cents: int
    starts_at: datetime
    ends_at: datetime
    phase: LotPhase


class PublicLotDetail(PublicLotSummary):
    external_id: int
    medium_display: str | None
    dimensions: str | None
    department_title: str | None
    artwork_type_title: str | None
    credit_line: str | None
    source_url: str
    min_increment_cents: int


class PublicLotsResponse(BaseModel):
    as_of: datetime
    live: list[PublicLotSummary]
    scheduled: list[PublicLotSummary]
    ended: list[PublicLotSummary]


class PublicLotDetailResponse(BaseModel):
    as_of: datetime
    lot: PublicLotDetail


def _clock_cte() -> CTE:
    """`clock_timestamp()` avaliado uma única vez: o CTE `MATERIALIZED` nunca é
    embutido na consulta, então o valor se repete em todas as linhas."""
    return (
        select(func.clock_timestamp().label("as_of"))
        .cte("clock")
        .prefix_with("MATERIALIZED")
    )


def public_snapshot_statement() -> Select:
    """O único statement da vitrine: o instante e todos os lotes no mesmo snapshot.
    O `LEFT OUTER JOIN` parte do CTE (uma linha), então há `as_of` mesmo sem lotes."""
    clock = _clock_cte()
    return select(clock.c.as_of, Lot).select_from(clock).outerjoin(Lot, true())


def read_public_snapshot(session: Session) -> tuple[datetime, list[Lot]]:
    rows = session.execute(public_snapshot_statement()).all()
    as_of = rows[0].as_of.astimezone(UTC)
    return as_of, [row.Lot for row in rows if row.Lot is not None]


def read_public_lot_snapshot(
    session: Session, lot_id: uuid.UUID
) -> tuple[datetime, Lot | None]:
    # A condição do id fica no JOIN, nunca num WHERE: o WHERE apagaria a linha do
    # `as_of` quando o lote não existe.
    clock = _clock_cte()
    row = session.execute(
        select(clock.c.as_of, Lot).select_from(clock).outerjoin(Lot, Lot.id == lot_id)
    ).one()
    return row.as_of.astimezone(UTC), row.Lot


def public_lot_summary(lot: Lot, as_of: datetime) -> PublicLotSummary:
    return PublicLotSummary(
        id=lot.id,
        title=lot.title,
        artist_display=lot.artist_display,
        date_display=lot.date_display,
        image_url=image_url_for(lot.image_id),
        starting_bid_cents=lot.starting_bid_cents,
        starts_at=lot.starts_at.astimezone(UTC),
        ends_at=lot.ends_at.astimezone(UTC),
        phase=lot_phase(lot.starts_at, lot.ends_at, as_of),
    )


def public_lot_detail(lot: Lot, as_of: datetime) -> PublicLotDetail:
    return PublicLotDetail(
        **public_lot_summary(lot, as_of).model_dump(),
        external_id=lot.external_id,
        medium_display=lot.medium_display,
        dimensions=lot.dimensions,
        department_title=lot.department_title,
        artwork_type_title=lot.artwork_type_title,
        credit_line=lot.credit_line,
        source_url=lot.source_url,
        min_increment_cents=lot.min_increment_cents,
    )


def build_public_lots(lots: list[Lot], as_of: datetime) -> PublicLotsResponse:
    """Classifica todos os lotes com o MESMO `as_of` e ordena cada grupo (P4, D3):
    ao vivo `ends_at ASC`, agendados `starts_at ASC`, encerrados `ends_at DESC`;
    `id ASC` desempata nos três."""
    by_phase: dict[LotPhase, list[Lot]] = {phase: [] for phase in LotPhase}
    for lot in lots:
        by_phase[lot_phase(lot.starts_at, lot.ends_at, as_of)].append(lot)
    live = sorted(by_phase[LotPhase.LIVE], key=lambda lot: (lot.ends_at, lot.id))
    scheduled = sorted(
        by_phase[LotPhase.SCHEDULED], key=lambda lot: (lot.starts_at, lot.id)
    )
    # `reverse=True` preserva a estabilidade: o `id ASC` do primeiro sort sobrevive.
    ended = sorted(by_phase[LotPhase.ENDED], key=lambda lot: lot.id)
    ended.sort(key=lambda lot: lot.ends_at, reverse=True)
    return PublicLotsResponse(
        as_of=as_of,
        live=[public_lot_summary(lot, as_of) for lot in live],
        scheduled=[public_lot_summary(lot, as_of) for lot in scheduled],
        ended=[public_lot_summary(lot, as_of) for lot in ended],
    )


def _violation_response(violation: ScheduleViolation) -> Response:
    field = (
        "starts_at"
        if violation == ScheduleViolation.STARTS_AT_NOT_IN_FUTURE
        else "ends_at"
    )
    return error_response(
        422,
        "validation_error",
        details=[{"loc": ["body", field], "type": violation.value}],
        headers=NO_STORE,
    )


def register_lot_routes(app: FastAPI) -> None:
    @api_route(
        app,
        "/api/lots",
        methods=["POST"],
        policy=AccessPolicy.AUCTIONEER,
        status_code=201,
        response_model=LotResponse,
        responses=error_responses(401, 403, 422, 503),
    )
    def create(
        body: CreateLotRequest,
        response: Response,
        user: User = Depends(require_auctioneer),
        session: Session = Depends(get_session),
        client: ArticClient = Depends(get_artic_client),
    ) -> LotResponse | Response:
        # D1: guardo o id antes do rollback (que expira o `User`) e encerro a
        # leitura da autenticação antes da AIC. Nenhuma transação fica aberta
        # durante a chamada externa, que leva até alguns segundos.
        auctioneer_id = user.id
        session.rollback()

        # Validação que não depende de `now` sai antes da AIC (não gasta a cota).
        if ends_not_after_scheduled_start(body.starts_at, body.ends_at):
            return _violation_response(ScheduleViolation.ENDS_AT_NOT_AFTER_START)

        try:
            resolved = resolve_artwork_for_lot(client, body.external_id)
        except CatalogUnavailable as error:
            # Só a categoria vai ao log: nunca o corpo, o usuário nem a resposta da AIC.
            logger.warning(
                "artic request failed: operation=create_lot reason=%s", error.reason
            )
            return error_response(503, CATALOG_UNAVAILABLE, headers=NO_STORE)
        if isinstance(resolved, ArtworkRefusal):
            logger.info("lot creation refused: reason=%s", resolved)
            return error_response(422, ARTWORK_NOT_ELIGIBLE, headers=NO_STORE)

        # Transação de escrita: um único instante do banco para as regras e para o
        # `created_at`; a transação só insere e confirma.
        now = database_now(session)
        result = create_lot(
            session,
            snapshot=resolved,
            terms=body,
            auctioneer_id=auctioneer_id,
            now=now,
        )
        if isinstance(result, ScheduleViolation):
            session.rollback()
            return _violation_response(result)
        session.commit()

        response.headers["Cache-Control"] = "no-store"
        return lot_response(result)

    # Registrada antes de `/api/lots/{lot_id}` (2.5, D4): senão "mine" cairia no
    # parâmetro.
    @api_route(
        app,
        "/api/lots/mine",
        methods=["GET"],
        policy=AccessPolicy.AUCTIONEER,
        response_model=MyLotsResponse,
        responses=error_responses(401, 403),
    )
    def my_lots(
        response: Response,
        user: User = Depends(require_auctioneer),
        session: Session = Depends(get_session),
    ) -> MyLotsResponse:
        # Leitura pura (AD-19): só SELECT, só o dono da sessão, sem a AIC, sem limite.
        lots = session.scalars(
            select(Lot)
            .where(Lot.auctioneer_id == user.id)
            .order_by(Lot.created_at.desc(), Lot.id.desc())
        ).all()
        response.headers["Cache-Control"] = "no-store"
        return MyLotsResponse(items=[lot_response(lot) for lot in lots])

    @api_route(
        app,
        "/api/lots",
        methods=["GET"],
        policy=AccessPolicy.PUBLIC,
        response_model=PublicLotsResponse,
    )
    def public_lots(
        response: Response, session: Session = Depends(get_session)
    ) -> PublicLotsResponse:
        # Leitura pública (AD-19): um único statement `SELECT`, sem trava, sem a AIC e
        # sem sessão. O instante e as linhas vêm do mesmo snapshot (P2 refinada).
        as_of, lots = read_public_snapshot(session)
        result = build_public_lots(lots, as_of)
        session.rollback()  # encerra a transação de leitura antes da resposta (D2)
        response.headers["Cache-Control"] = "no-store"
        return result

    # Sempre depois de `/api/lots/mine` (D4).
    @api_route(
        app,
        "/api/lots/{lot_id}",
        methods=["GET"],
        policy=AccessPolicy.PUBLIC,
        response_model=PublicLotDetailResponse,
        responses=error_responses(404, 422),
    )
    def public_lot(
        lot_id: uuid.UUID,
        response: Response,
        session: Session = Depends(get_session),
    ) -> PublicLotDetailResponse | Response:
        as_of, lot = read_public_lot_snapshot(session, lot_id)
        result = (
            None
            if lot is None
            else PublicLotDetailResponse(as_of=as_of, lot=public_lot_detail(lot, as_of))
        )
        session.rollback()
        if result is None:
            return error_response(404, "not_found", headers=NO_STORE)
        response.headers["Cache-Control"] = "no-store"
        return result
