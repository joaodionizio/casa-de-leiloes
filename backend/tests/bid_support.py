"""Apoio dos testes de lance (Story 3.4): licitantes e lotes prontos, o serviço numa
sessão própria, fotografia do banco, reconstrução independente da cadeia, adulteração
direta, remoção determinística de CHECKs e observadores de statements. Dinheiro sempre
como parâmetro inteiro, nunca `float`."""

import re
import threading
import uuid
from collections.abc import Callable, Iterator
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import timedelta
from typing import Any

import pytest
from sqlalchemy import event, text
from sqlalchemy.engine import Connection, Engine, make_url
from sqlalchemy.orm import Session, sessionmaker

from app import bids
from app.bid_integrity import (
    GENESIS_HASH,
    AnchorState,
    CanonicalBid,
    VerifiableBid,
    generate_bidder_alias,
    verify_anchor_hmac,
    verify_bid_chain,
)
from app.bids import place_bid
from app.config import IntegrityConfig
from app.seed import DEMO_AUCTIONEER_ID
from tests.db_guard import assert_connection_is_test_database
from tests.lot_support import (  # noqa: F401  (reexportados para os testes de lance)
    db_now,
    insert_lot,
    integrity_secrets,
    normalized,
)

TABLES_WITH_DROPPABLE_CHECKS = frozenset({"lots", "bids"})
IDENTIFIER = re.compile(r"[a-z][a-z0-9_]*")


def integrity() -> IntegrityConfig:
    audit, pseudonym = integrity_secrets()
    return IntegrityConfig(audit_hmac_secret=audit, pseudonym_secret=pseudonym)


# --- cenário ---


def add_bidder(factory: sessionmaker[Session], total: int = 0) -> uuid.UUID:
    """Um `BIDDER` novo, com carteira, além dos dois semeados."""
    user_id = uuid.uuid4()
    with factory() as session:
        session.execute(
            text(
                "INSERT INTO users (id, email, password_hash, role) "
                "VALUES (:id, :email, 'hash', 'BIDDER')"
            ),
            {"id": user_id, "email": f"{user_id}@example.com"},
        )
        session.execute(
            text(
                "INSERT INTO wallets (user_id, total_balance_cents, "
                "committed_balance_cents) VALUES (:id, :total, 0)"
            ),
            {"id": user_id, "total": total},
        )
        session.commit()
    return user_id


def live_lot(factory: sessionmaker[Session], **columns: Any) -> uuid.UUID:
    """Lote ao vivo e assinado (início -1 h, fim +1 h por padrão). Os usuários
    semeados precisam existir (o leiloeiro do seed é o dono)."""
    now = db_now(factory)
    row: dict[str, Any] = {
        "auctioneer_id": DEMO_AUCTIONEER_ID,
        "starts_at": now - timedelta(hours=1),
        "ends_at": now + timedelta(hours=1),
    }
    row.update(columns)
    return insert_lot(factory, **row)


# --- o serviço ---


def run_bid(
    factory: sessionmaker[Session],
    lot_id: uuid.UUID,
    bidder_id: uuid.UUID,
    amount: int,
) -> Any:
    """O serviço numa `Session` própria: confirma se aceito, senão desfaz. Devolve o
    resultado do serviço."""
    with factory() as session:
        result = place_bid(
            session,
            lot_id=lot_id,
            bidder_id=bidder_id,
            amount_cents=amount,
            integrity=integrity(),
        )
        if isinstance(result, bids.PlacedBid):
            session.commit()
        else:
            session.rollback()
        return result


def hold_bid(
    session: Session, lot_id: uuid.UUID, bidder_id: uuid.UUID, amount: int
) -> Any:
    """O serviço sem confirmar: a sessão segue segurando as travas."""
    return place_bid(
        session,
        lot_id=lot_id,
        bidder_id=bidder_id,
        amount_cents=amount,
        integrity=integrity(),
    )


# --- leitura direta ---


def lot_state(factory: sessionmaker[Session], lot_id: uuid.UUID) -> dict[str, Any]:
    with factory() as session:
        row = session.execute(
            text("SELECT * FROM lots WHERE id = :id"), {"id": lot_id}
        ).one()
    return dict(row._mapping)


def bid_rows(factory: sessionmaker[Session], lot_id: uuid.UUID) -> list[dict[str, Any]]:
    with factory() as session:
        return [
            dict(row._mapping)
            for row in session.execute(
                text("SELECT * FROM bids WHERE lot_id = :id ORDER BY sequence"),
                {"id": lot_id},
            )
        ]


def db_snapshot(factory: sessionmaker[Session]) -> tuple[list, list, list]:
    """`(lots, bids, wallets)` completos e ordenados: a comparação "nada mudou"."""
    with factory() as session:
        lots = [
            tuple(row)
            for row in session.execute(text("SELECT * FROM lots ORDER BY id"))
        ]
        placed = [
            tuple(row)
            for row in session.execute(
                text("SELECT * FROM bids ORDER BY lot_id, sequence")
            )
        ]
        wallets = [
            tuple(row)
            for row in session.execute(text("SELECT * FROM wallets ORDER BY user_id"))
        ]
    return lots, placed, wallets


# --- verificação independente (primitives da 3.3, sem passar por `app.bids`) ---


def assert_authenticated(factory: sessionmaker[Session], lot_id: uuid.UUID) -> None:
    """Cadeia, âncora (segredo de auditoria) e vínculo operacional do líder."""
    audit, pseudonym = integrity_secrets()
    lot = lot_state(factory, lot_id)
    rows = bid_rows(factory, lot_id)
    records = tuple(
        VerifiableBid(
            bid=CanonicalBid(
                v=row["canonical_version"],
                lot_id=row["lot_id"],
                sequence=row["sequence"],
                bidder_alias=row["bidder_alias"],
                amount_cents=row["amount_cents"],
                timestamp=row["placed_at"],
                previous_hash=row["previous_hash"],
            ),
            current_hash=row["current_hash"],
        )
        for row in rows
    )
    assert verify_bid_chain(records, lot_id=lot_id)
    assert [row["sequence"] for row in rows] == list(range(1, len(rows) + 1))
    assert lot["bid_count"] == len(rows)
    assert lot["final_hash"] == (rows[-1]["current_hash"] if rows else GENESIS_HASH)
    state = AnchorState(
        v=1, lot_id=lot_id, bid_count=lot["bid_count"], final_hash=lot["final_hash"]
    )
    assert lot["anchor_hmac"] is not None
    assert verify_anchor_hmac(state, lot["anchor_hmac"], audit_hmac_secret=audit)
    assert not verify_anchor_hmac(
        state, lot["anchor_hmac"], audit_hmac_secret=pseudonym
    )
    if rows:
        last = rows[-1]
        assert lot["current_bid_cents"] == last["amount_cents"]
        assert lot["current_leader_id"] == last["bidder_id"]
        assert last["bidder_alias"] == generate_bidder_alias(
            lot_id=lot_id, user_id=last["bidder_id"], pseudonym_secret=pseudonym
        )
    else:
        assert lot["current_bid_cents"] is None
        assert lot["current_leader_id"] is None


def assert_invariants(factory: sessionmaker[Session]) -> None:
    """I1 a I5 em todos os lotes assinados e carteiras. Só vale quando todo
    comprometido nasceu de lance (não de `set_wallet`)."""
    with factory() as session:
        lot_ids = [
            row[0]
            for row in session.execute(
                text("SELECT id FROM lots WHERE anchor_hmac IS NOT NULL")
            )
        ]
        wallets = session.execute(
            text(
                "SELECT user_id, total_balance_cents, committed_balance_cents "
                "FROM wallets"
            )
        ).all()
        led = dict(
            session.execute(
                text(
                    "SELECT current_leader_id, sum(current_bid_cents)::bigint "
                    "FROM lots WHERE current_leader_id IS NOT NULL "
                    "AND cancelled_at IS NULL "
                    "AND NOT EXISTS (SELECT 1 FROM lot_settlements "
                    "WHERE lot_settlements.lot_id = lots.id) "
                    "GROUP BY current_leader_id"
                )
            ).all()
        )
        forks = session.execute(
            text(
                "SELECT count(*) FROM (SELECT 1 FROM bids "
                "GROUP BY lot_id, previous_hash HAVING count(*) > 1) forked"
            )
        ).scalar_one()
    for lot_id in lot_ids:
        assert_authenticated(factory, lot_id)  # I1, I4
    assert forks == 0  # I5
    for user_id, total, committed in wallets:
        assert 0 <= committed <= total  # I2
        assert committed == led.get(user_id, 0)  # I3


def tamper(factory: sessionmaker[Session], sql: str, **params: Any) -> int:
    """Adulteração direta por SQL, como faria quem escreve no banco."""
    with factory() as session:
        result = session.execute(text(sql), params)
        session.commit()
        return result.rowcount


# --- observadores de statements ---


def is_lot_lock(statement: str) -> bool:
    upper = normalized(statement).upper()
    return upper.startswith("SELECT") and "FROM LOTS" in upper and "FOR UPDATE" in upper


class StatementWatch:
    """Avisa quando `expected` statements que casam com `matcher` foram vistos."""

    def __init__(self, matcher: Callable[[str], bool], expected: int = 1) -> None:
        self.matcher = matcher
        self.expected = expected
        self.seen = 0
        self.reached = threading.Event()
        self._lock = threading.Lock()

    def __call__(self, conn, cursor, statement, parameters, context, executemany):  # type: ignore[no-untyped-def]
        if not self.matcher(statement):
            return
        with self._lock:
            self.seen += 1
            if self.seen >= self.expected:
                self.reached.set()


@contextmanager
def watch_statement(
    engine: Engine, matcher: Callable[[str], bool], expected: int = 1
) -> Iterator[StatementWatch]:
    watch = StatementWatch(matcher, expected)
    event.listen(engine, "before_cursor_execute", watch)
    try:
        yield watch
    finally:
        event.remove(engine, "before_cursor_execute", watch)


@contextmanager
def before_statement(
    engine: Engine,
    marker: Callable[[str], bool],
    action: Callable[[], None],
    *,
    once_per_thread: bool = True,
) -> Iterator[None]:
    """Roda `action()` imediatamente antes do statement que casa com `marker`, uma vez
    por thread (ou sempre, se `once_per_thread=False`). Ponto de injeção
    determinístico, sem `sleep`; `action` usa uma conexão própria."""
    fired: set[int] = set()

    def listener(conn, cursor, statement, parameters, context, executemany):  # type: ignore[no-untyped-def]
        thread = threading.get_ident()
        if marker(statement) and not (once_per_thread and thread in fired):
            fired.add(thread)
            action()

    event.listen(engine, "before_cursor_execute", listener)
    try:
        yield
    finally:
        event.remove(engine, "before_cursor_execute", listener)


def call_log(monkeypatch: pytest.MonkeyPatch) -> list[str]:
    """Envolve, em `app.bids`, os primitives públicos que o serviço usa. Cada chamada
    anota o nome e delega à função real. A ordem semântica se prova por eles, não pelo
    nome do helper do gate."""
    events: list[str] = []

    def wrap(name: str) -> None:
        real = getattr(bids, name)

        def wrapper(*args: Any, **kwargs: Any) -> Any:
            events.append(name)
            return real(*args, **kwargs)

        monkeypatch.setattr(bids, name, wrapper)

    for name in (
        "lock_lot",
        "database_now",
        "verify_bid_chain",
        "verify_anchor_hmac",
        "evaluate_pre_wallet",
        "lock_wallet",
        "evaluate_post_wallet",
        "available_cents",
    ):
        wrap(name)
    return events


# --- remoção determinística de CHECKs (N-02, D17) ---


@dataclass(frozen=True)
class CheckDefinition:
    table: str
    name: str
    definition: str


def read_checks(connection: Connection, names: list[str]) -> dict[str, CheckDefinition]:
    rows = connection.execute(
        text(
            "SELECT c.conname, t.relname, pg_get_constraintdef(c.oid) "
            "FROM pg_constraint c "
            "JOIN pg_class t ON t.oid = c.conrelid "
            "JOIN pg_namespace n ON n.oid = t.relnamespace "
            "WHERE c.contype = 'c' AND n.nspname = 'public' "
            "AND c.conname = ANY(:names)"
        ),
        {"names": names},
    ).all()
    return {
        name: CheckDefinition(table, name, definition)
        for name, table, definition in rows
    }


@pytest.fixture
def drop_checks(
    db_engine: Engine, test_database_url: str
) -> Iterator[Callable[..., None]]:
    """`drop(*names)` remove CHECKs de `lots` ou `bids` para estados que só um atacante
    com DDL cria. Recusa (antes de qualquer `DROP`) nome ausente e constraint de outra
    tabela. A definição real vem de `pg_get_constraintdef` antes do `DROP`; ao final,
    mesmo com o teste falhando, os dados são limpos, só as removidas são recriadas com a
    definição capturada e o catálogo é conferido (nunca fica schema contaminado)."""
    database = make_url(test_database_url).database or ""
    captured: dict[str, CheckDefinition] = {}

    def drop(*names: str) -> None:
        assert all(IDENTIFIER.fullmatch(name) for name in names), names
        with db_engine.begin() as connection:
            assert_connection_is_test_database(connection, database)
            found = read_checks(connection, list(names))
            missing = sorted(set(names) - set(found))
            if missing:
                raise AssertionError(f"CHECK inexistente: {missing}")
            outside = sorted(
                d.name
                for d in found.values()
                if d.table not in TABLES_WITH_DROPPABLE_CHECKS
            )
            if outside:
                raise AssertionError(f"CHECK fora de lots e bids: {outside}")
            for definition in found.values():
                captured[definition.name] = definition
                connection.execute(
                    text(
                        f"ALTER TABLE {definition.table} "  # noqa: S608
                        f"DROP CONSTRAINT {definition.name}"
                    )
                )

    try:
        yield drop
    finally:
        if captured:
            with db_engine.begin() as connection:
                assert_connection_is_test_database(connection, database)
                connection.execute(
                    text("TRUNCATE receipts, lot_settlements, bids, lots")
                )
                present = read_checks(connection, list(captured))
                for definition in captured.values():
                    if definition.name not in present:
                        connection.execute(
                            text(
                                f"ALTER TABLE {definition.table} "  # noqa: S608
                                f"ADD CONSTRAINT {definition.name} "
                                f"{definition.definition}"
                            )
                        )
            with db_engine.connect() as connection:
                after = read_checks(connection, list(captured))
                connection.rollback()
            assert after == captured, "o catálogo de CHECKs ficou diferente"


# --- gravador de statements com parâmetros e classificação ---


class StatementLog:
    """Todo statement do engine, na ordem, com os parâmetros. A mesma ferramenta de
    `statement_recorder`, mais os parâmetros (para provar a ordem das carteiras)."""

    def __init__(self) -> None:
        self.entries: list[tuple[str, Any]] = []
        self._lock = threading.Lock()

    def __call__(self, conn, cursor, statement, parameters, context, executemany):  # type: ignore[no-untyped-def]
        with self._lock:
            self.entries.append((normalized(statement), parameters))

    @property
    def statements(self) -> list[str]:
        return [statement for statement, _ in self.entries]

    def count(self, fragment: str) -> int:
        return sum(1 for s in self.statements if fragment.upper() in s.upper())

    def saw(self, fragment: str) -> bool:
        return self.count(fragment) > 0


@contextmanager
def statement_log(engine: Engine) -> Iterator[StatementLog]:
    log = StatementLog()
    event.listen(engine, "before_cursor_execute", log)
    try:
        yield log
    finally:
        event.remove(engine, "before_cursor_execute", log)


def kind_of(statement: str) -> str | None:
    """Os statements do serviço de lance, por tipo; qualquer outro vira `None`."""
    upper = statement.upper()
    if upper.startswith("SELECT") and "CLOCK_TIMESTAMP" in upper:
        return "clock"
    if upper.startswith("SELECT") and "FROM LOTS" in upper and "FOR UPDATE" in upper:
        return "lock_lot"
    if upper.startswith("SELECT") and "FROM WALLETS" in upper and "FOR UPDATE" in upper:
        return "lock_wallet"
    if upper.startswith("SELECT") and "FROM BIDS" in upper:
        return "history"
    if upper.startswith("UPDATE WALLETS"):
        return "update_wallets"
    if upper.startswith("INSERT INTO BIDS"):
        return "insert_bid"
    if upper.startswith("UPDATE LOTS"):
        return "update_lot"
    return None


def service_trace(log: StatementLog) -> list[str]:
    """A sequência de tipos do serviço, com repetições consecutivas colapsadas
    (`UPDATE wallets` de duas linhas pode sair em um ou dois statements)."""
    trace: list[str] = []
    for statement in log.statements:
        kind = kind_of(statement)
        if kind is not None and (
            not trace or trace[-1] != kind or kind == "lock_wallet"
        ):
            trace.append(kind)
    return trace


def locked_wallet_ids(log: StatementLog) -> list[uuid.UUID]:
    """Os `user_id` das travas de carteira, na ordem em que foram pedidas."""
    ids: list[uuid.UUID] = []
    for statement, parameters in log.entries:
        if kind_of(statement) == "lock_wallet":
            values = (
                list(parameters.values())
                if isinstance(parameters, dict)
                else list(parameters)
            )
            ids.append(values[0])
    return ids


def lot_update_columns(log: StatementLog) -> list[str]:
    """As colunas do `SET` do `UPDATE lots` (deve haver um só)."""
    updates = [s for s in log.statements if kind_of(s) == "update_lot"]
    assert len(updates) == 1, updates
    clause = updates[0].split(" SET ", 1)[1].split(" WHERE ", 1)[0]
    return [assignment.split("=")[0].strip() for assignment in clause.split(",")]
