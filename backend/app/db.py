from collections.abc import Iterator
from functools import lru_cache

from sqlalchemy import MetaData, create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.config import get_settings, normalize_database_url

NAMING_CONVENTION = {
    "ix": "ix_%(column_0_label)s",
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}


class Base(DeclarativeBase):
    metadata = MetaData(naming_convention=NAMING_CONVENTION)


def create_db_engine(url: str) -> Engine:
    # `hide_parameters` (Story 2.2, P16): o SQLAlchemy não renderiza os valores dos
    # parâmetros na mensagem do erro. O `DETAIL` escrito pelo próprio PostgreSQL
    # pode conter valores (UNIQUE: a chave; CHECK: a linha inteira).
    return create_engine(
        normalize_database_url(url), pool_pre_ping=True, hide_parameters=True
    )


def create_session_factory(engine: Engine) -> sessionmaker[Session]:
    return sessionmaker(bind=engine, expire_on_commit=False)


@lru_cache
def get_engine() -> Engine:
    """Engine da aplicação, criado na primeira requisição que precisa de banco."""
    return create_db_engine(get_settings().database_url.get_secret_value())


def get_session() -> Iterator[Session]:
    """Dependência `def` (threadpool): uma `Session` curta por requisição, sem
    commit automático. Os testes a substituem por `dependency_overrides`."""
    with create_session_factory(get_engine())() as session:
        yield session
