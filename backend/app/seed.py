"""Contas e lote demo de demonstração (Story 2.2 e 2.4, AD-24, P8, P12, P13).

Idempotente. Usuários: `INSERT ... ON CONFLICT (id) DO NOTHING`, nunca `UPDATE`; uma
conta que já existe nunca é recriada nem alterada, nem o hash. Carteiras (Story 3.1):
todo usuário sem carteira ganha uma zerada, só `INSERT`; saldo existente nunca é
alterado e nenhum saldo demo é pré-carregado. Lote demo: só `INSERT`,
e só quando não há demo realmente aberto (`is_demo` e `ends_at > agora do banco`);
um lote antigo nunca é alterado nem apagado.

Offline: o lote vem de uma fixture versionada (`seed_data/demo_artwork.json`) e passa
pelo mesmo `create_lot` da criação manual, que não fala com a rede. O seed não
consulta o catálogo do museu nem usa cliente HTTP.

`python -m app.seed` precisa só de `DATABASE_URL`; não importa `app.main`, que
exige `APP_ORIGIN` e `JWT_SECRET`.
"""

import logging
import uuid
from datetime import datetime, timedelta
from pathlib import Path
from typing import NamedTuple

from sqlalchemy import exists, func, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from app.config import get_settings
from app.db import create_db_engine, create_session_factory
from app.lots import (
    ArtworkSnapshot,
    Lot,
    LotTerms,
    ScheduleViolation,
    create_lot,
    database_now,
)
from app.security import hash_password
from app.users import User, UserRole
from app.wallet import ensure_wallets

logger = logging.getLogger(__name__)

# Credencial pública de demonstração, documentada no README: não é segredo.
DEMO_PASSWORD = "Demo123!"


class SeedUser(NamedTuple):
    id: uuid.UUID
    email: str
    role: UserRole


# IDs gerados uma vez e versionados; não são segredo.
SEED_USERS = (
    SeedUser(
        uuid.UUID("219e37a5-0def-4b26-87d4-b08668f7c112"),
        "auctioneer@example.com",
        UserRole.AUCTIONEER,
    ),
    SeedUser(
        uuid.UUID("64d28807-1bfc-47cd-950e-37dbf962d7af"),
        "bidder1@example.com",
        UserRole.BIDDER,
    ),
    SeedUser(
        uuid.UUID("b5e863a7-4317-4a28-a622-9182cfa00842"),
        "bidder2@example.com",
        UserRole.BIDDER,
    ),
)

DEMO_AUCTIONEER_ID = next(
    seed.id for seed in SEED_USERS if seed.role == UserRole.AUCTIONEER
)

# Chave da trava consultiva que serializa dois seeds simultâneos (ASCII "casaseed").
SEED_ADVISORY_LOCK_KEY = 0x6361736173656564
DEMO_LOT_DURATION = timedelta(hours=72)
DEMO_STARTING_BID_CENTS = 10_000  # R$ 100,00
DEMO_MIN_INCREMENT_CENTS = 1_000  # R$ 10,00
# Dentro de `backend/app`: a imagem de produção copia essa pasta (o `.dockerignore`
# exclui `backend/tests`, então uma fixture de teste não chegaria lá).
DEMO_ARTWORK_PATH = Path(__file__).resolve().parent / "seed_data" / "demo_artwork.json"


def seed_users(session: Session) -> int:
    """Insere as contas ausentes e devolve quantas inseriu. Não faz commit.

    Calcula o Argon2 só para as ausentes. Um e-mail semeado já usado por outro
    `id` deixa a `IntegrityError` de `uq_users_email` propagar.
    """
    ids = [seed.id for seed in SEED_USERS]
    existing = set(session.scalars(select(User.id).where(User.id.in_(ids))))
    missing = [seed for seed in SEED_USERS if seed.id not in existing]
    if not missing:
        return 0
    rows = [
        {
            "id": seed.id,
            "email": seed.email,
            "password_hash": hash_password(DEMO_PASSWORD),
            "role": seed.role.value,
        }
        for seed in missing
    ]
    # `RETURNING`: o `rowcount` do psycopg não é confiável em INSERT multilinha, e
    # só as linhas de fato inseridas (sem conflito) voltam.
    inserted = session.execute(
        insert(User)
        .values(rows)
        .on_conflict_do_nothing(index_elements=[User.id])
        .returning(User.id)
    )
    return len(inserted.all())


def load_demo_artwork() -> ArtworkSnapshot:
    """Fixture local → snapshot. Campo a mais ou a menos reprova o boot com erro
    claro, sem rede."""
    return ArtworkSnapshot.model_validate_json(DEMO_ARTWORK_PATH.read_bytes())


def acquire_seed_lock(session: Session) -> None:
    """Trava de transação: liberada sozinha no commit ou no rollback, mesmo se o
    processo morrer. Um segundo seed espera aqui até o primeiro terminar."""
    session.execute(select(func.pg_advisory_xact_lock(SEED_ADVISORY_LOCK_KEY)))


def seed_demo_lot(session: Session, now: datetime) -> bool:
    """Cria um lote demo se não houver um realmente aberto; devolve se criou.

    "Aberto" (Q4) = `is_demo` e `ends_at > now`. Nunca faz `UPDATE` nem `DELETE`.
    """
    open_demo = session.scalar(
        select(exists().where(Lot.is_demo.is_(True), Lot.ends_at > now))
    )
    if open_demo:
        return False
    terms = LotTerms(
        starting_bid_cents=DEMO_STARTING_BID_CENTS,
        min_increment_cents=DEMO_MIN_INCREMENT_CENTS,
        starts_at=None,
        ends_at=now + DEMO_LOT_DURATION,
    )
    result = create_lot(
        session,
        snapshot=load_demo_artwork(),
        terms=terms,
        auctioneer_id=DEMO_AUCTIONEER_ID,
        now=now,
        is_demo=True,
    )
    if isinstance(result, ScheduleViolation):
        # Impossível com 72 h a partir de `now`: falha alto em vez de silenciar.
        raise RuntimeError(f"demo lot rejected by the schedule rule: {result.value}")
    return True


def run_seed(session: Session) -> tuple[int, bool]:
    """Uma transação para usuários, carteiras e lote; não faz commit. A trava é o
    primeiro statement; o instante do banco é lido depois dela (análogo ao AD-6) e
    decide tudo: "existe demo aberto?", `starts_at`, `created_at` e a base de
    `ends_at`."""
    acquire_seed_lock(session)
    users = seed_users(session)  # o leiloeiro precisa existir antes do lote (FK)
    # Todo usuário sem carteira, não só os semeados. A contagem não entra no retorno
    # nem no log: o log do seed só afirma o que já foi confirmado pelo commit.
    ensure_wallets(session)
    now = database_now(session)
    created = seed_demo_lot(session, now)
    return users, created


def main() -> None:
    logging.basicConfig(level=logging.INFO)
    engine = create_db_engine(get_settings().database_url.get_secret_value())
    try:
        with create_session_factory(engine)() as session:
            inserted, created = run_seed(session)
            session.commit()  # libera a trava consultiva
    finally:
        engine.dispose()
    logger.info(
        "seed: %d user(s) inserted; demo lot %s",
        inserted,
        "created" if created else "kept",
    )


if __name__ == "__main__":
    main()
