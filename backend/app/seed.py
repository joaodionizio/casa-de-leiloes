"""Contas de demonstração (Story 2.2, AD-24, P12, P13).

Idempotente: `INSERT ... ON CONFLICT (id) DO NOTHING`, nunca `UPDATE`. Uma conta
que já existe nunca é recriada nem alterada, nem o hash. Só usuários: não cria
lote nem consulta a API externa.

`python -m app.seed` precisa só de `DATABASE_URL`; não importa `app.main`, que
exige `APP_ORIGIN` e `JWT_SECRET`.
"""

import logging
import uuid
from typing import NamedTuple

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from app.config import get_settings
from app.db import create_db_engine, create_session_factory
from app.security import hash_password
from app.users import User, UserRole

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


def main() -> None:
    logging.basicConfig(level=logging.INFO)
    engine = create_db_engine(get_settings().database_url.get_secret_value())
    try:
        with create_session_factory(engine)() as session:
            inserted = seed_users(session)
            session.commit()
    finally:
        engine.dispose()
    logger.info("seed: %d user(s) inserted", inserted)


if __name__ == "__main__":
    main()
