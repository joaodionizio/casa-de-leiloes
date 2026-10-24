from functools import lru_cache
from pathlib import Path

from pydantic import SecretStr, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict
from sqlalchemy.engine import make_url

POSTGRES_DRIVER = "postgresql+psycopg"

BACKEND_DIR = Path(__file__).resolve().parent.parent
ENV_FILE = BACKEND_DIR / ".env"


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
