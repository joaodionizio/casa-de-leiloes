from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from pydantic import ValidationError
from sqlalchemy import create_engine, text
from sqlalchemy.engine import make_url
from sqlalchemy.exc import OperationalError

from app.config import get_origin_settings, get_settings
from tests.db_guard import (
    UnsafeTestDatabaseError,
    assert_connected_to_test_database,
    assert_connection_is_test_database,
    assert_safe_test_target,
)

ALEMBIC_INI = Path(__file__).resolve().parent.parent / "alembic.ini"
COMPOSE_HINT = "Suba o banco com: docker compose up -d --wait postgres"

_test_database_url: str | None = None


def alembic_config(database_url: str) -> Config:
    config = Config(str(ALEMBIC_INI))
    config.attributes["database_url"] = database_url
    config.attributes["configure_logger"] = False
    return config


def reset_test_database(test_url: str) -> None:
    """Recria o schema public do banco _test e aplica as migrations."""
    engine = create_engine(test_url, isolation_level="AUTOCOMMIT")
    try:
        with engine.connect() as connection:
            # Defesa em profundidade: a conexão que vai executar o DROP confirma
            # o banco antes de qualquer operação destrutiva.
            assert_connection_is_test_database(
                connection, make_url(test_url).database or ""
            )
            connection.execute(text("DROP SCHEMA IF EXISTS public CASCADE"))
            connection.execute(text("CREATE SCHEMA public"))
    finally:
        engine.dispose()
    command.upgrade(alembic_config(test_url), "head")


def pytest_sessionstart(session: pytest.Session) -> None:
    """Prepara o banco de teste uma vez por sessão; nunca pula, falha com mensagem."""
    global _test_database_url
    try:
        settings = get_settings()
    except ValidationError as error:
        pytest.exit(
            "Configuração inválida (DATABASE_URL / TEST_DATABASE_URL): "
            + "; ".join(f"{e['loc'][0]}: {e['msg']}" for e in error.errors()),
            returncode=3,
        )
    try:
        get_origin_settings()
    except ValidationError:
        pytest.exit(
            "APP_ORIGIN ausente ou inválida (ex.: http://localhost:5173)",
            returncode=3,
        )
    test_secret = settings.test_database_url
    try:
        test_url = assert_safe_test_target(
            test_secret.get_secret_value() if test_secret else None,
            settings.database_url.get_secret_value(),
        )
        assert_connected_to_test_database(test_url)
        reset_test_database(test_url)
    except UnsafeTestDatabaseError as error:
        pytest.exit(f"Unsafe test database: {error}", returncode=3)
    except OperationalError:
        pytest.exit(
            f"PostgreSQL de teste inacessível. {COMPOSE_HINT}",
            returncode=3,
        )
    _test_database_url = test_url


@pytest.fixture(scope="session")
def test_database_url() -> str:
    assert _test_database_url is not None
    return _test_database_url
