from functools import lru_cache

from pydantic import SecretStr, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict
from sqlalchemy.engine import make_url

POSTGRES_DRIVER = "postgresql+psycopg"


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
        env_file=".env",
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
