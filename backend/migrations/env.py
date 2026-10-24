from logging.config import fileConfig

from alembic import context
from sqlalchemy import create_engine, pool

from app.config import get_settings, normalize_database_url
from app.db import Base

config = context.config

if config.config_file_name is not None and config.attributes.get(
    "configure_logger", True
):
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def get_url() -> str:
    # Chamadas programáticas (testes) passam a URL em config.attributes, para
    # nunca tocar o banco de dev nem passar a senha pelo ConfigParser.
    url = config.attributes.get("database_url")
    if url is None:
        url = get_settings().database_url.get_secret_value()
    return normalize_database_url(url)


def run_migrations_offline() -> None:
    context.configure(
        url=get_url(),
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    connectable = create_engine(get_url(), poolclass=pool.NullPool)
    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
