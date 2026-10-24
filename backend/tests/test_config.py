import pytest
from app.config import Settings, normalize_database_url
from pydantic import ValidationError
from sqlalchemy.engine import make_url


def test_postgresql_scheme_becomes_psycopg() -> None:
    result = make_url(normalize_database_url("postgresql://u:p@db.example:5433/app"))
    assert result.drivername == "postgresql+psycopg"


def test_psycopg_scheme_passes_unchanged() -> None:
    url = "postgresql+psycopg://u:p@localhost:5432/app"
    assert normalize_database_url(url) == url


def test_components_are_preserved() -> None:
    url = "postgresql://us%40er:p%2Fa%3Ass%25@db.example:5433/app_db?sslmode=require&connect_timeout=5"
    result = make_url(normalize_database_url(url))
    assert result.username == "us@er"
    assert result.password == "p/a:ss%"
    assert result.host == "db.example"
    assert result.port == 5433
    assert result.database == "app_db"
    assert dict(result.query) == {"sslmode": "require", "connect_timeout": "5"}


@pytest.mark.parametrize(
    "url",
    [
        "sqlite:///data.db",
        "postgresql+psycopg2://u:secret-pw@localhost/app",
        "mysql+pymysql://u:secret-pw@localhost/app",
    ],
)
def test_other_drivers_are_rejected_without_leaking_password(url: str) -> None:
    with pytest.raises(ValueError) as error:
        normalize_database_url(url)
    assert "secret-pw" not in str(error.value)


def test_garbage_url_is_rejected_without_leaking_input() -> None:
    with pytest.raises(ValueError) as error:
        normalize_database_url("not a url secret-pw")
    assert "secret-pw" not in str(error.value)


def test_settings_normalize_and_hide_secrets() -> None:
    settings = Settings(
        _env_file=None,
        database_url="postgresql://u:secret-pw@localhost/app_dev",
        test_database_url="postgresql://u:secret-pw@localhost/app_test",
    )
    assert settings.database_url.get_secret_value().startswith("postgresql+psycopg://")
    assert "secret-pw" not in repr(settings)


def test_settings_validation_error_does_not_leak_password() -> None:
    with pytest.raises(ValidationError) as error:
        Settings(_env_file=None, database_url="sqlite://u:secret-pw@localhost/app")
    assert "secret-pw" not in str(error.value)
