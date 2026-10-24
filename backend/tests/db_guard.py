from sqlalchemy import create_engine, text
from sqlalchemy.engine import Connection, make_url

from app.config import normalize_database_url

TEST_DB_SUFFIX = "_test"


class UnsafeTestDatabaseError(RuntimeError):
    """O alvo dos testes não é um banco de teste seguro para apagar."""


def assert_safe_test_target(test_url: str | None, dev_url: str | None) -> str:
    """Valida o alvo antes de qualquer DROP e devolve a URL de teste normalizada.

    As mensagens nunca incluem a URL, para não vazar a senha.
    """
    if not test_url:
        raise UnsafeTestDatabaseError(
            "TEST_DATABASE_URL is not set; refusing to run integration tests."
        )
    normalized_test = normalize_database_url(test_url)
    if dev_url and normalize_database_url(dev_url) == normalized_test:
        raise UnsafeTestDatabaseError(
            "TEST_DATABASE_URL is equal to DATABASE_URL; refusing to reset it."
        )
    database = make_url(normalized_test).database or ""
    if not database.endswith(TEST_DB_SUFFIX):
        raise UnsafeTestDatabaseError(
            f"TEST_DATABASE_URL database must end with {TEST_DB_SUFFIX!r}; "
            "refusing to reset it."
        )
    return normalized_test


def assert_connection_is_test_database(connection: Connection, expected: str) -> None:
    """Confirma no servidor, pela própria conexão, que o banco é o _test esperado."""
    actual = connection.execute(text("SELECT current_database()")).scalar_one()
    if actual != expected or not actual.endswith(TEST_DB_SUFFIX):
        raise UnsafeTestDatabaseError(
            "current_database() is not the expected _test database; "
            "refusing to reset it."
        )


def assert_connected_to_test_database(test_url: str) -> None:
    """Segunda guarda, antes do reset: abre uma conexão só para confirmar o banco."""
    engine = create_engine(test_url)
    try:
        with engine.connect() as connection:
            assert_connection_is_test_database(
                connection, make_url(test_url).database or ""
            )
    finally:
        engine.dispose()
