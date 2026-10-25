"""Apoio dos testes de lotes (Story 2.4): corpo válido, leitura direta da tabela e
um gravador de statements."""

import uuid
from collections.abc import Iterator
from contextlib import contextmanager
from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy import event, text
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

LOT_COLUMNS = [
    "id",
    "auctioneer_id",
    "external_id",
    "title",
    "artist_display",
    "date_display",
    "medium_display",
    "dimensions",
    "department_title",
    "artwork_type_title",
    "image_id",
    "credit_line",
    "source_url",
    "starting_bid_cents",
    "min_increment_cents",
    "starts_at",
    "ends_at",
    "is_demo",
    "created_at",
]
IMAGE_ID = "2d484387-2509-5e8e-2c43-22f9981972eb"


def iso(moment: datetime) -> str:
    return moment.astimezone(UTC).isoformat().replace("+00:00", "Z")


def db_now(factory: sessionmaker[Session]) -> datetime:
    with factory() as session:
        return session.execute(text("SELECT clock_timestamp()")).scalar_one()


def valid_body(factory: sessionmaker[Session], **overrides: Any) -> dict[str, Any]:
    """27992, R$ 1.250,00 e R$ 50,00, início agora e fim amanhã (pelo relógio do
    banco). Um valor `...` em `overrides` remove a chave."""
    body: dict[str, Any] = {
        "external_id": 27992,
        "starting_bid_cents": 125000,
        "min_increment_cents": 5000,
        "starts_at": None,
        "ends_at": iso(db_now(factory) + timedelta(days=1)),
    }
    for key, value in overrides.items():
        if value is ...:
            body.pop(key, None)
        else:
            body[key] = value
    return body


def count_lots(factory: sessionmaker[Session]) -> int:
    with factory() as session:
        return session.execute(text("SELECT count(*) FROM lots")).scalar_one()


def lot_rows(factory: sessionmaker[Session]) -> list[tuple]:
    columns = ", ".join(LOT_COLUMNS)
    with factory() as session:
        return [
            tuple(row)
            for row in session.execute(
                text(f"SELECT {columns} FROM lots ORDER BY id")  # noqa: S608
            )
        ]


def insert_lot(factory: sessionmaker[Session], **columns: Any) -> uuid.UUID:
    """Insere um lote por SQL direto, para estados que a API não cria (demo vencido,
    lote de outro leiloeiro). Obrigatórios: `auctioneer_id`. O resto tem padrão."""
    now = db_now(factory)
    row: dict[str, Any] = {
        "id": uuid.uuid4(),
        "external_id": 27992,
        "title": "Obra de teste",
        "artist_display": "Artista",
        "date_display": None,
        "medium_display": None,
        "dimensions": None,
        "department_title": None,
        "artwork_type_title": None,
        "image_id": IMAGE_ID,
        "credit_line": None,
        "source_url": "https://www.artic.edu/artworks/27992",
        "starting_bid_cents": 10000,
        "min_increment_cents": 1000,
        "starts_at": now - timedelta(hours=2),
        "ends_at": now + timedelta(hours=2),
        "is_demo": False,
        "created_at": now,
    }
    row.update(columns)
    names = ", ".join(row)
    params = ", ".join(f":{name}" for name in row)
    with factory() as session:
        session.execute(
            text(f"INSERT INTO lots ({names}) VALUES ({params})"),  # noqa: S608
            row,
        )
        session.commit()
    return row["id"]


class StatementRecorder:
    def __init__(self) -> None:
        self.statements: list[str] = []

    def __call__(self, conn, cursor, statement, parameters, context, executemany):  # type: ignore[no-untyped-def]
        self.statements.append(statement)


@contextmanager
def statement_recorder(engine: Engine) -> Iterator[StatementRecorder]:
    """Registra todo statement executado no engine enquanto o bloco roda."""
    recorder = StatementRecorder()
    event.listen(engine, "before_cursor_execute", recorder)
    try:
        yield recorder
    finally:
        event.remove(engine, "before_cursor_execute", recorder)
