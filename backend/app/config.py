from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

from pydantic import SecretStr, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict
from sqlalchemy.engine import make_url

from app.csrf import format_origin, parse_origin

POSTGRES_DRIVER = "postgresql+psycopg"

BACKEND_DIR = Path(__file__).resolve().parent.parent
ENV_FILE = BACKEND_DIR / ".env"

MIN_JWT_SECRET_LENGTH = 32
LOCAL_HTTP_HOSTS = frozenset({"localhost", "127.0.0.1", "::1"})
SESSION_COOKIE_NAME = "auction_session"
SECURE_SESSION_COOKIE_NAME = f"__Host-{SESSION_COOKIE_NAME}"


def normalize_database_url(url: str) -> str:
    """Normaliza para o dialect psycopg 3, por componentes da URL.

    Aceita `postgresql` (formato do Render) e `postgresql+psycopg`; qualquer
    outro driver é recusado. A mensagem de erro nunca inclui a URL.
    """
    try:
        parsed = make_url(url)
    except Exception:
        raise ValueError("database URL is not a valid SQLAlchemy URL") from None
    if parsed.drivername == "postgresql":
        parsed = parsed.set(drivername=POSTGRES_DRIVER)
    elif parsed.drivername != POSTGRES_DRIVER:
        raise ValueError(
            f"unsupported database driver {parsed.drivername!r}; "
            "use postgresql:// or postgresql+psycopg://"
        )
    return parsed.render_as_string(hide_password=False)


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=ENV_FILE,
        extra="ignore",
        hide_input_in_errors=True,
    )

    database_url: SecretStr
    test_database_url: SecretStr | None = None

    @field_validator("database_url", "test_database_url", mode="before")
    @classmethod
    def _normalize_url(cls, value: object) -> object:
        if isinstance(value, str):
            return normalize_database_url(value)
        return value


@lru_cache
def get_settings() -> Settings:
    return Settings()  # type: ignore[call-arg]  # database_url vem do ambiente


class SpaSettings(BaseSettings):
    """Onde está o build da SPA. Separado de `Settings` para que importar a
    aplicação não exija `DATABASE_URL`."""

    model_config = SettingsConfigDict(env_file=ENV_FILE, extra="ignore")

    spa_dist_dir: Path | None = None

    @field_validator("spa_dist_dir")
    @classmethod
    def _relative_to_backend_dir(cls, value: Path | None) -> Path | None:
        # Caminho relativo vale a partir de backend/, nunca do cwd do processo.
        if value is not None and not value.is_absolute():
            return BACKEND_DIR / value
        return value


@lru_cache
def get_spa_settings() -> SpaSettings:
    return SpaSettings()


class OriginSettings(BaseSettings):
    """A origem pública que aceita escritas (AD-29, Story 2.1 P3). Separado de
    `Settings` para que importar a aplicação não exija `DATABASE_URL`."""

    model_config = SettingsConfigDict(
        env_file=ENV_FILE, extra="ignore", hide_input_in_errors=True
    )

    app_origin: str

    @field_validator("app_origin")
    @classmethod
    def _canonical_origin(cls, value: str) -> str:
        origin = parse_origin(value) if value == value.strip() else None
        if origin is None:
            raise ValueError(
                "APP_ORIGIN must be scheme://host[:port] (http or https), "
                "with no path, query, fragment or credentials"
            )
        return format_origin(origin)


@lru_cache
def get_origin_settings() -> OriginSettings:
    return OriginSettings()  # type: ignore[call-arg]  # app_origin vem do ambiente


class AuthSettings(BaseSettings):
    """O segredo do JWT (Story 2.2, P1). Separado de `Settings` para que importar
    a aplicação não exija `DATABASE_URL`. O valor nunca aparece em erro, log ou
    resposta."""

    model_config = SettingsConfigDict(
        env_file=ENV_FILE, extra="ignore", hide_input_in_errors=True
    )

    jwt_secret: SecretStr

    @field_validator("jwt_secret")
    @classmethod
    def _long_enough(cls, value: SecretStr) -> SecretStr:
        if len(value.get_secret_value()) < MIN_JWT_SECRET_LENGTH:
            raise ValueError(
                f"JWT_SECRET must have at least {MIN_JWT_SECRET_LENGTH} characters"
            )
        return value


@lru_cache
def get_auth_settings() -> AuthSettings:
    return AuthSettings()  # type: ignore[call-arg]  # jwt_secret vem do ambiente


@dataclass(frozen=True)
class SessionConfig:
    """Tudo o que a sessão precisa, montado uma vez em `create_app()`."""

    jwt_secret: SecretStr
    cookie_name: str
    cookie_secure: bool


def session_cookie_for_origin(canonical_origin: str) -> tuple[str, bool]:
    """Nome e `Secure` do cookie de sessão, derivados só da `APP_ORIGIN` (P4).

    `https` usa `__Host-` com `Secure`; `http` só vale para localhost, 127.0.0.1 ou
    ::1, sem `Secure`. Outro host em `http` é recusado, sem ecoar a origem.
    """
    origin = parse_origin(canonical_origin)
    if origin is None:
        raise ValueError("APP_ORIGIN must be scheme://host[:port]")
    scheme, host, _ = origin
    if scheme == "https":
        return SECURE_SESSION_COOKIE_NAME, True
    if host in LOCAL_HTTP_HOSTS:
        return SESSION_COOKIE_NAME, False
    raise ValueError(
        "APP_ORIGIN must use https unless the host is localhost, 127.0.0.1 or ::1"
    )
