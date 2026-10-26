import pytest
from pydantic import SecretStr, ValidationError
from sqlalchemy.engine import make_url

from app import main
from app.config import (
    AuditSettings,
    AuthSettings,
    IntegrityConfig,
    IntegritySettings,
    OriginSettings,
    Settings,
    integrity_config,
    normalize_database_url,
)
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


# --- JWT_SECRET (Story 2.2, P1) ---

JWT_SECRET_OK = "s" * 32
JWT_SECRET_SHORT = "p" * 31


@pytest.mark.parametrize("raw", ["", JWT_SECRET_SHORT, "curto"])
def test_short_or_empty_jwt_secret_is_rejected_without_the_value(raw: str) -> None:
    with pytest.raises(ValidationError) as error:
        AuthSettings(_env_file=None, jwt_secret=raw)
    message = str(error.value)
    if raw:
        assert raw not in message


def test_missing_jwt_secret_is_rejected(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("JWT_SECRET", raising=False)
    with pytest.raises(ValidationError):
        AuthSettings(_env_file=None)


def test_jwt_secret_with_32_characters_is_accepted() -> None:
    settings = AuthSettings(_env_file=None, jwt_secret=JWT_SECRET_OK)
    assert settings.jwt_secret.get_secret_value() == JWT_SECRET_OK
    assert JWT_SECRET_OK not in repr(settings)


def test_jwt_secret_is_read_from_the_environment(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("JWT_SECRET", JWT_SECRET_OK)
    assert AuthSettings(_env_file=None).jwt_secret.get_secret_value() == JWT_SECRET_OK


def test_create_app_rejects_a_short_jwt_secret_without_echoing_it() -> None:
    with pytest.raises(ValidationError) as error:
        create_app(app_origin="https://casa.example", jwt_secret="curto")
    assert "curto" not in str(error.value)


def test_create_app_fails_without_jwt_secret(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("JWT_SECRET", raising=False)
    monkeypatch.setattr(main, "get_auth_settings", lambda: AuthSettings(_env_file=None))
    with pytest.raises(ValidationError):
        create_app(app_origin="https://casa.example")


# --- modo do cookie pela APP_ORIGIN (Story 2.2, P4, OQ-1) ---


def build_session_config(origin: str):
    app = create_app(app_origin=origin, jwt_secret=JWT_SECRET_OK)
    return app.state.session_config


def test_https_origin_uses_the_host_prefixed_secure_cookie() -> None:
    session_config = build_session_config("https://casa.example")
    assert session_config.cookie_name == "__Host-auction_session"
    assert session_config.cookie_secure is True


@pytest.mark.parametrize(
    "origin",
    ["http://localhost:5173", "http://127.0.0.1:8000", "http://[::1]:5173"],
)
def test_local_http_origin_uses_the_plain_cookie_without_secure(origin: str) -> None:
    session_config = build_session_config(origin)
    assert session_config.cookie_name == "auction_session"
    assert session_config.cookie_secure is False


@pytest.mark.parametrize(
    "origin",
    ["http://casa.example", "http://192.168.0.10:8000", "http://localhost.evil"],
)
def test_remote_http_origin_stops_create_app_without_echoing_it(origin: str) -> None:
    # `OriginSettings` continua aceitando a origem (testes da 2.1 inalterados).
    assert OriginSettings(_env_file=None, app_origin=origin).app_origin
    with pytest.raises(ValueError) as error:
        create_app(app_origin=origin, jwt_secret=JWT_SECRET_OK)
    message = str(error.value)
    assert "https" in message
    assert origin not in message
    assert "casa.example" not in message
    assert "192.168" not in message


def test_session_config_never_shows_the_secret() -> None:
    session_config = build_session_config("https://casa.example")
    assert JWT_SECRET_OK not in repr(session_config)


# --- AUDIT_HMAC_SECRET e PSEUDONYM_SECRET (Story 3.4, P5, T-SECRETS) ---

AUDIT_OK = "a" * 32
PSEUDONYM_OK = "p" * 32
TWO_BYTE_OK = "é" * 16  # 16 caracteres, 32 bytes em UTF-8
TWO_BYTE_SHORT = "é" * 15 + "a"  # 16 caracteres, 31 bytes


@pytest.mark.parametrize("raw", ["", "curto", "x" * 31, TWO_BYTE_SHORT])
def test_a_short_audit_secret_is_rejected_by_bytes_without_the_value(raw: str) -> None:
    with pytest.raises(ValidationError) as error:
        AuditSettings(_env_file=None, audit_hmac_secret=raw)
    if raw:
        assert raw not in str(error.value)


def test_the_size_is_counted_in_utf8_bytes_not_characters() -> None:
    assert len(TWO_BYTE_OK) == 16 and len(TWO_BYTE_OK.encode("utf-8")) == 32
    assert AuditSettings(_env_file=None, audit_hmac_secret=TWO_BYTE_OK)
    assert IntegritySettings(
        _env_file=None, audit_hmac_secret=AUDIT_OK, pseudonym_secret=TWO_BYTE_OK
    )


def test_a_missing_audit_secret_is_rejected(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("AUDIT_HMAC_SECRET", raising=False)
    with pytest.raises(ValidationError):
        AuditSettings(_env_file=None)


def test_audit_settings_does_not_need_the_pseudonym_secret(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("PSEUDONYM_SECRET", raising=False)
    monkeypatch.setenv("AUDIT_HMAC_SECRET", AUDIT_OK)
    settings = AuditSettings(_env_file=None)
    assert settings.audit_hmac_secret.get_secret_value() == AUDIT_OK
    assert AUDIT_OK not in repr(settings)


@pytest.mark.parametrize("raw", ["", "curto", TWO_BYTE_SHORT])
def test_a_short_pseudonym_secret_is_rejected_without_the_value(raw: str) -> None:
    with pytest.raises(ValidationError) as error:
        IntegritySettings(
            _env_file=None, audit_hmac_secret=AUDIT_OK, pseudonym_secret=raw
        )
    if raw:
        assert raw not in str(error.value)


def test_a_missing_pseudonym_secret_is_rejected(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("PSEUDONYM_SECRET", raising=False)
    with pytest.raises(ValidationError):
        IntegritySettings(_env_file=None, audit_hmac_secret=AUDIT_OK)


def test_equal_audit_and_pseudonym_secrets_are_rejected_without_the_value() -> None:
    with pytest.raises(ValidationError) as error:
        IntegritySettings(
            _env_file=None, audit_hmac_secret=AUDIT_OK, pseudonym_secret=AUDIT_OK
        )
    assert AUDIT_OK not in str(error.value)
    assert "must be different" in str(error.value)


def test_a_surrogate_in_the_environment_fails_without_the_character() -> None:
    with pytest.raises(ValidationError) as error:
        AuditSettings(_env_file=None, audit_hmac_secret="\udc80" * 40)
    assert "\udc80" not in str(error.value) and "\\udc80" not in str(error.value)


def test_the_settings_and_the_config_never_show_the_secrets() -> None:
    settings = IntegritySettings(
        _env_file=None, audit_hmac_secret=AUDIT_OK, pseudonym_secret=PSEUDONYM_OK
    )
    config = integrity_config(settings, SecretStr(JWT_SECRET_OK))

    assert AUDIT_OK not in repr(settings) and PSEUDONYM_OK not in repr(settings)
    assert AUDIT_OK not in repr(config) and PSEUDONYM_OK not in repr(config)
    assert "bytes" not in repr(config) and "b'" not in repr(config)
    assert config == IntegrityConfig(AUDIT_OK.encode(), PSEUDONYM_OK.encode())


@pytest.mark.parametrize("which", ["audit", "pseudonym"])
def test_a_secret_equal_to_the_jwt_secret_is_rejected_without_the_value(
    which: str,
) -> None:
    jwt = "j" * 32
    settings = IntegritySettings(
        _env_file=None,
        audit_hmac_secret=jwt if which == "audit" else AUDIT_OK,
        pseudonym_secret=jwt if which == "pseudonym" else PSEUDONYM_OK,
    )
    with pytest.raises(ValueError) as error:
        integrity_config(settings, SecretStr(jwt))
    assert jwt not in str(error.value)
    assert "must differ from JWT_SECRET" in str(error.value)


def test_create_app_keeps_the_integrity_secrets_as_bytes_in_the_app_state() -> None:
    app = create_app(
        app_origin="https://casa.example",
        jwt_secret=JWT_SECRET_OK,
        audit_hmac_secret=AUDIT_OK,
        pseudonym_secret=PSEUDONYM_OK,
    )
    assert app.state.integrity_config == IntegrityConfig(
        AUDIT_OK.encode(), PSEUDONYM_OK.encode()
    )


@pytest.mark.parametrize(
    ("audit", "pseudonym", "jwt"),
    [
        ("curto", PSEUDONYM_OK, JWT_SECRET_OK),
        (AUDIT_OK, "curto", JWT_SECRET_OK),
        (AUDIT_OK, AUDIT_OK, JWT_SECRET_OK),
        (JWT_SECRET_OK, PSEUDONYM_OK, JWT_SECRET_OK),
        (AUDIT_OK, JWT_SECRET_OK, JWT_SECRET_OK),
    ],
)
def test_create_app_refuses_to_start_with_invalid_integrity_secrets(
    audit: str, pseudonym: str, jwt: str
) -> None:
    with pytest.raises(ValueError) as error:
        create_app(
            app_origin="https://casa.example",
            jwt_secret=jwt,
            audit_hmac_secret=audit,
            pseudonym_secret=pseudonym,
        )
    for value in {audit, pseudonym, jwt}:
        if value != "curto":
            assert value not in str(error.value)
    assert "curto" not in str(error.value)


def test_create_app_fails_without_the_integrity_secrets(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("AUDIT_HMAC_SECRET", raising=False)
    monkeypatch.delenv("PSEUDONYM_SECRET", raising=False)
    monkeypatch.setattr(
        main, "get_integrity_settings", lambda: IntegritySettings(_env_file=None)
    )
    with pytest.raises(ValidationError):
        create_app(app_origin="https://casa.example", jwt_secret=JWT_SECRET_OK)
