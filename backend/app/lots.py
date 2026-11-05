"""Lotes (Story 2.4, AD-3, AD-6, AD-12, AD-23, AD-26, AD-30).

Modelo, schemas e regras do lote; consultas SQL em `lot_queries.py` e rotas
HTTP em `lot_routes.py`. Dois
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
from typing import TYPE_CHECKING, Annotated, Literal

from fastapi import FastAPI, Request
from pydantic import (
    AfterValidator,
    AwareDatetime,
    BaseModel,
    BeforeValidator,
    ConfigDict,
    Field,
    StrictInt,
    StringConstraints,
    model_validator,
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
    text,
)
from sqlalchemy.orm import Mapped, Session, mapped_column
from sqlalchemy.sql.expression import CTE

from app.artic import IMAGE_ID_PATTERN, ArticClient
from app.bid_integrity import GENESIS_HASH, AnchorState, compute_anchor_hmac
from app.catalog import (
    MAX_EXTERNAL_ID,
    ArtworkDetail,
    LookupStatus,
    get_artwork,
    image_url_for,
)
from app.config import IntegrityConfig
from app.db import Base
from app.lot_time import LotPhase, lot_phase
from app.money import MAX_CENTS, Cents

if TYPE_CHECKING:
    from app.bids import IntegrityConflict

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
    """Espelha as migrations `0003`, `0005` e `0006`; o esquema dos testes vem sempre
    delas.

    `anchor_hmac` nulo é o lote legado, não autenticado: recusa lance (Story 3.4).
    `cancelled_at` (Story 3.6) nulo = não cancelado. Toda escrita em `bids`, no estado
    de lance **e em `cancelled_at`** passa pela trava do lote (`lock_lot`); só o
    serviço de cancelamento (`app.lot_cancellation`) escreve `cancelled_at`, e nada o
    limpa. A âncora v1 não o cobre."""

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
        CheckConstraint(
            f"current_bid_cents > 0 AND current_bid_cents <= {MAX_CENTS}",
            name="current_bid_range",
        ),
        CheckConstraint(
            "current_bid_cents >= starting_bid_cents",
            name="current_bid_at_least_starting",
        ),
        CheckConstraint(
            "(current_bid_cents IS NULL) = (current_leader_id IS NULL)",
            name="current_bid_with_leader",
        ),
        CheckConstraint(
            "(bid_count = 0) = (current_bid_cents IS NULL)",
            name="bid_count_matches_current_bid",
        ),
        CheckConstraint("bid_count >= 0", name="bid_count_non_negative"),
        CheckConstraint("final_hash ~ '^[0-9a-f]{64}$'", name="final_hash_format"),
        CheckConstraint(
            f"bid_count > 0 OR final_hash = '{GENESIS_HASH}'",
            name="empty_lot_is_genesis",
        ),
        CheckConstraint("anchor_hmac ~ '^[0-9a-f]{64}$'", name="anchor_hmac_format"),
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
    # Estado de lance (Story 3.4). Só `create_lot` e `app.bids.place_bid` escrevem
    # nestas colunas, o segundo sempre sob a trava do lote (`lock_lot`).
    current_bid_cents: Mapped[int | None] = mapped_column(BigInteger)
    current_leader_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT")
    )
    bid_count: Mapped[int] = mapped_column(BigInteger, server_default=text("0"))
    final_hash: Mapped[str] = mapped_column(
        Text, server_default=text(f"'{GENESIS_HASH}'")
    )
    anchor_hmac: Mapped[str | None] = mapped_column(Text)
    cancelled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


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


def lock_lot(session: Session, lot_id: uuid.UUID) -> Lot | None:
    """Trava a linha do lote (`SELECT ... FOR UPDATE`) e devolve o estado confirmado
    mais recente. Só a tabela `lots`, sem `JOIN`: a releitura depois da espera vale
    para a linha travada, e a cadeia é lida num statement posterior (Story 3.4, D2).
    `populate_existing` força a releitura mesmo que a `Session` já tenha o objeto."""
    return session.scalars(
        select(Lot)
        .where(Lot.id == lot_id)
        .with_for_update()
        .execution_options(populate_existing=True)
    ).one_or_none()


def get_integrity_config(request: Request) -> IntegrityConfig:
    config: IntegrityConfig = request.app.state.integrity_config
    return config


def create_lot(
    session: Session,
    *,
    snapshot: ArtworkSnapshot,
    terms: LotTerms,
    auctioneer_id: uuid.UUID,
    now: datetime,
    audit_hmac_secret: bytes,
    is_demo: bool = False,
) -> Lot | ScheduleViolation:
    """Aplica a regra de horário e grava o lote, já com a âncora vazia assinada
    (`bid_count = 0`, hash genesis, HMAC do próprio `lot_id`). Sem rede: não recebe
    cliente HTTP nem consulta o catálogo. Não faz commit: quem chama decide.

    Só este caminho assina estado vazio, e o `id` vem do servidor: nenhum chamador
    consegue assinar um lote que já existe. A HMAC é calculada antes de o objeto
    existir; segredo inválido levanta `ValueError` sem ter adicionado nada."""
    schedule = resolve_schedule(terms.starts_at, terms.ends_at, now)
    if isinstance(schedule, ScheduleViolation):
        return schedule
    lot_id = uuid.uuid4()
    anchor_hmac = compute_anchor_hmac(
        AnchorState(v=1, lot_id=lot_id, bid_count=0, final_hash=GENESIS_HASH),
        audit_hmac_secret=audit_hmac_secret,
    )
    lot = Lot(
        id=lot_id,
        auctioneer_id=auctioneer_id,
        **snapshot.model_dump(),
        starting_bid_cents=terms.starting_bid_cents,
        min_increment_cents=terms.min_increment_cents,
        starts_at=schedule.starts_at,
        ends_at=schedule.ends_at,
        is_demo=is_demo,
        created_at=now,
        current_bid_cents=None,
        current_leader_id=None,
        bid_count=0,
        final_hash=GENESIS_HASH,
        anchor_hmac=anchor_hmac,
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


class PrivateLotSettlementSummary(BaseModel):
    """Whitelist privada: só valores persistidos, sem identidade ou prova técnica."""

    model_config = ConfigDict(extra="forbid")

    outcome: Literal["sold", "unsold"]
    winner_alias: (
        Annotated[str, StringConstraints(pattern=r"^Licitante-[0-9A-F]{16}$")] | None
    )
    final_amount_cents: Cents | None
    bid_count: Annotated[StrictInt, Field(ge=0, le=MAX_CENTS)]
    settled_at: ApiDatetime

    @model_validator(mode="after")
    def validate_outcome(self):
        if self.outcome == "sold":
            valid = (
                self.winner_alias is not None
                and self.final_amount_cents is not None
                and self.bid_count > 0
            )
        else:
            valid = (
                self.winner_alias is None
                and self.final_amount_cents is None
                and self.bid_count == 0
            )
        if not valid:
            raise ValueError("Resultado inválido.")
        self.settled_at = self.settled_at.astimezone(UTC)
        return self


class MyLotResponse(LotResponse):
    """Item da lista do leiloeiro (Story 3.6, D7): o `LotResponse` mais o cancelamento,
    a contagem persistida (dica de UX, não autenticada) e a fase temporal. O 201 da
    criação continua usando o `LotResponse`."""

    cancelled_at: datetime | None
    bid_count: int
    phase: LotPhase
    settlement_status: Literal["pending", "settled"]
    settlement: PrivateLotSettlementSummary | None


class MyLotsResponse(BaseModel):
    as_of: datetime
    items: list[MyLotResponse]
    total_received_cents: Annotated[StrictInt, Field(ge=0, le=MAX_CENTS)]


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


def my_lot_response(
    lot: Lot, as_of: datetime, settlement: PrivateLotSettlementSummary | None = None
) -> MyLotResponse:
    return MyLotResponse(
        **lot_response(lot).model_dump(),
        cancelled_at=(
            None if lot.cancelled_at is None else lot.cancelled_at.astimezone(UTC)
        ),
        bid_count=settlement.bid_count if settlement else lot.bid_count,
        phase=lot_phase(lot.starts_at, lot.ends_at, as_of),
        settlement_status="settled" if settlement else "pending",
        settlement=settlement,
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
    current_bid_cents: int | None
    starts_at: datetime
    ends_at: datetime
    phase: LotPhase
    settlement_status: Literal["pending", "settled"]


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
    from app.lot_queries import _clock_cte as query

    return query()


def public_snapshot_statement() -> Select:
    from app.lot_queries import public_snapshot_statement as query

    return query()


def my_lots_statement(auctioneer_id: uuid.UUID) -> Select:
    from app.lot_queries import my_lots_statement as query

    return query(auctioneer_id)


def read_my_lots_snapshot(
    session: Session, auctioneer_id: uuid.UUID
) -> "MyLotsResponse | IntegrityConflict":
    from app.lot_queries import read_my_lots_snapshot as query

    return query(session, auctioneer_id)


def read_public_snapshot(
    session: Session,
) -> tuple[datetime, list[Lot], set[uuid.UUID]]:
    from app.lot_queries import read_public_snapshot as query

    return query(session)


def read_public_lot_snapshot(
    session: Session, lot_id: uuid.UUID
) -> tuple[datetime, Lot | None, bool]:
    from app.lot_queries import read_public_lot_snapshot as query

    return query(session, lot_id)


def public_lot_summary(
    lot: Lot, as_of: datetime, *, has_settlement: bool
) -> PublicLotSummary:
    from app.lot_queries import public_lot_summary as query

    return query(lot, as_of, has_settlement=has_settlement)


def public_lot_detail(
    lot: Lot, as_of: datetime, *, has_settlement: bool
) -> PublicLotDetail:
    from app.lot_queries import public_lot_detail as query

    return query(lot, as_of, has_settlement=has_settlement)


def build_public_lots(
    lots: list[Lot], as_of: datetime, settled_lot_ids: set[uuid.UUID]
) -> PublicLotsResponse:
    from app.lot_queries import build_public_lots as query

    return query(lots, as_of, settled_lot_ids)


def register_lot_routes(app: FastAPI) -> None:
    """Compatibility entrypoint; HTTP routes live in a dedicated module."""
    from app.lot_routes import register_lot_routes as register

    register(app)
