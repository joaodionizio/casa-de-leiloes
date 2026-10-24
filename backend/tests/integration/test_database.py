from datetime import datetime

import pytest
from alembic.script import ScriptDirectory
from sqlalchemy import inspect, text
from sqlalchemy.engine import make_url
from sqlalchemy.orm import Session

from app.db import create_db_engine, create_session_factory
from tests.conftest import alembic_config, reset_test_database
from tests.db_guard import UnsafeTestDatabaseError


def test_clock_timestamp_returns_timezone_aware_datetime(
    test_database_url: str,
) -> None:
    engine = create_db_engine(test_database_url)
    try:
        with create_session_factory(engine)() as session:
            assert isinstance(session, Session)
            now = session.execute(text("SELECT clock_timestamp()")).scalar_one()
    finally:
        engine.dispose()
    assert isinstance(now, datetime)
    assert now.tzinfo is not None


def test_engine_uses_postgresql_dialect_with_psycopg_driver(
    test_database_url: str,
) -> None:
    engine = create_db_engine(test_database_url)
    try:
        assert engine.dialect.name == "postgresql"
        assert engine.dialect.driver == "psycopg"
    finally:
        engine.dispose()


def test_test_database_is_at_head_with_no_domain_tables(
    test_database_url: str,
) -> None:
    head = ScriptDirectory.from_config(
        alembic_config(test_database_url)
    ).get_current_head()
    engine = create_db_engine(test_database_url)
    try:
        with engine.connect() as connection:
            version = connection.execute(
                text("SELECT version_num FROM alembic_version")
            ).scalar_one()
            tables = inspect(connection).get_table_names(schema="public")
    finally:
        engine.dispose()
    assert version == head
    assert tables == ["alembic_version"]


def test_reset_refuses_non_test_database_before_dropping(
    test_database_url: str,
) -> None:
    non_test_url = make_url(test_database_url).set(database="postgres")
    with pytest.raises(UnsafeTestDatabaseError):
        reset_test_database(non_test_url.render_as_string(hide_password=False))
