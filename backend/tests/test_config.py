import pytest
from pydantic import ValidationError
from sqlalchemy.engine import make_url

from app.config import OriginSettings, Settings, normalize_database_url
from app.main import create_app


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


# --- APP_ORIGIN (Story 2.1) ---


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        (
            "https://casa-de-leiloes-i1xr.onrender.com",
            "https://casa-de-leiloes-i1xr.onrender.com",
        ),
        ("http://localhost:5173", "http://localhost:5173"),
        ("HTTPS://Casa.Example", "https://casa.example"),
        ("https://casa.example:443", "https://casa.example"),
        ("http://casa.example:80", "http://casa.example"),
        ("https://casa.example:8443", "https://casa.example:8443"),
        ("http://[::1]:5173", "http://[::1]:5173"),
    ],
)
def test_app_origin_is_normalized(raw: str, expected: str) -> None:
    assert OriginSettings(_env_file=None, app_origin=raw).app_origin == expected


@pytest.mark.parametrize(
    "raw",
    [
        "",
        " https://casa.example",
        "https://casa.example ",
        "https://casa.example/",
        "https://casa.example/path",
        "https://casa.example?x=1",
        "https://casa.example#frag",
        "https://user:pw@casa.example",
        "ftp://casa.example",
        "casa.example",
        "*",
        "null",
    ],
)
def test_invalid_app_origin_is_rejected_without_echoing_it(raw: str) -> None:
    with pytest.raises(ValidationError) as error:
        OriginSettings(_env_file=None, app_origin=raw)
    message = str(error.value)
    assert "pw@" not in message
    if raw.strip():
        assert raw.strip() not in message


def test_missing_app_origin_is_rejected(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("APP_ORIGIN", raising=False)
    with pytest.raises(ValidationError):
        OriginSettings(_env_file=None)


def test_app_origin_is_read_from_the_environment(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("APP_ORIGIN", "https://Casa.Example:443")
    assert OriginSettings(_env_file=None).app_origin == "https://casa.example"


def test_create_app_rejects_an_invalid_origin_argument() -> None:
    with pytest.raises(ValidationError):
        create_app(app_origin="lixo")
