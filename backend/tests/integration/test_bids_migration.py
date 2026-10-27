"""A migration `0005` no PostgreSQL real (Story 3.4, T-MIG, CAP-6).

Estrutura (colunas, tipos, nulos, defaults, nomes de constraints), cada CHECK recusando
pelo nome, os literais iguais aos da aplicação, o backfill dos lotes que já existiam e o
`downgrade`. Dinheiro sempre como parâmetro inteiro."""

import uuid
from collections.abc import Iterator
from datetime import UTC, datetime, timedelta
from typing import Any

import pytest
from alembic import command
from sqlalchemy import inspect, text
from sqlalchemy.engine import Engine
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, sessionmaker

from app.bid_integrity import GENESIS_HASH
from app.money import MAX_CENTS
from app.seed import DEMO_AUCTIONEER_ID
from tests.auth_support import BIDDER_EMAIL, seeded_id
from tests.bid_support import bid_rows, lot_state
from tests.conftest import alembic_config
from tests.lot_support import IMAGE_ID, LOT_COLUMNS, insert_lot
from tests.wallet_support import seed_users_with_wallets

NEW_LOT_COLUMNS = [
    "current_bid_cents",
    "current_leader_id",
    "bid_count",
    "final_hash",
    "anchor_hmac",
]
BID_COLUMNS = [
    "lot_id",
    "sequence",
    "bidder_id",
    "bidder_alias",
    "amount_cents",
    "placed_at",
    "previous_hash",
    "current_hash",
    "canonical_version",
]
HASH_A = "a" * 64
HASH_B = "b" * 64
NOW = datetime(2026, 10, 24, 12, 0, 0, tzinfo=UTC)


@pytest.fixture
def seeded(
    db_session_factory: sessionmaker[Session], clean_users: None
) -> sessionmaker[Session]:
    seed_users_with_wallets(db_session_factory)
    return db_session_factory


@pytest.fixture
def bidder() -> uuid.UUID:
    return seeded_id(BIDDER_EMAIL)


def constraint_of(error: pytest.ExceptionInfo[IntegrityError]) -> str:
    return str(error.value.orig)


def lot_with(seeded: sessionmaker[Session], **columns: Any) -> uuid.UUID:
    return insert_lot(
        seeded, anchored=False, auctioneer_id=DEMO_AUCTIONEER_ID, **columns
    )


def bid_values(
    lot_id: uuid.UUID, bidder: uuid.UUID, **overrides: Any
) -> dict[str, Any]:
    row: dict[str, Any] = {
        "lot_id": lot_id,
        "sequence": 1,
        "bidder_id": bidder,
        "bidder_alias": "Licitante-0123456789ABCDEF",
        "amount_cents": 10000,
        "placed_at": NOW,
        "previous_hash": GENESIS_HASH,
        "current_hash": HASH_A,
        "canonical_version": 1,
    }
    row.update(overrides)
    return row


def insert_bid(seeded: sessionmaker[Session], row: dict[str, Any]) -> None:
    columns = ", ".join(row)
    params = ", ".join(f":{name}" for name in row)
    with seeded() as session:
        session.execute(
            text(f"INSERT INTO bids ({columns}) VALUES ({params})"),  # noqa: S608
            row,
        )
        session.commit()


# --- estrutura de `lots` ---


def test_lots_gets_the_five_columns_after_the_existing_ones(db_engine: Engine) -> None:
    columns = {c["name"]: c for c in inspect(db_engine).get_columns("lots")}

    assert list(columns) == LOT_COLUMNS
    # A 0006 (Story 3.6) acrescenta `cancelled_at` depois destas cinco.
    assert LOT_COLUMNS[-6:-1] == NEW_LOT_COLUMNS
    for name in ("current_bid_cents", "current_leader_id", "anchor_hmac"):
        assert columns[name]["nullable"] is True, name
        assert columns[name]["default"] is None, name
    for name in ("bid_count", "final_hash"):
        assert columns[name]["nullable"] is False, name
    assert str(columns["bid_count"]["default"]) == "0"
    assert GENESIS_HASH in str(columns["final_hash"]["default"])


def test_lots_new_column_types_are_the_real_postgresql_types(db_engine: Engine) -> None:
    with db_engine.connect() as connection:
        types = dict(
            connection.execute(
                text(
                    "SELECT column_name, data_type FROM information_schema.columns "
                    "WHERE table_name = 'lots' AND table_schema = 'public'"
                )
            ).all()
        )
    assert types["current_bid_cents"] == "bigint"
    assert types["current_leader_id"] == "uuid"
    assert types["bid_count"] == "bigint"
    assert types["final_hash"] == "text"
    assert types["anchor_hmac"] == "text"


def test_lot_check_and_foreign_key_names_are_exact(db_engine: Engine) -> None:
    inspector = inspect(db_engine)
    checks = {c["name"] for c in inspector.get_check_constraints("lots")}

    assert checks >= {
        "ck_lots_current_bid_range",
        "ck_lots_current_bid_at_least_starting",
        "ck_lots_current_bid_with_leader",
        "ck_lots_bid_count_matches_current_bid",
        "ck_lots_bid_count_non_negative",
        "ck_lots_final_hash_format",
        "ck_lots_empty_lot_is_genesis",
        "ck_lots_anchor_hmac_format",
    }
    foreign_keys = {fk["name"]: fk for fk in inspector.get_foreign_keys("lots")}
    leader = foreign_keys["fk_lots_current_leader_id_users"]
    assert leader["referred_table"] == "users"
    assert leader["constrained_columns"] == ["current_leader_id"]
    assert leader["options"].get("ondelete") == "RESTRICT"
    # Sem índice novo em `lots` e sem `UNIQUE` (a mesma obra pode virar vários lotes).
    assert [i["name"] for i in inspector.get_indexes("lots")] == [
        "ix_lots_auctioneer_id"
    ]
    assert inspector.get_unique_constraints("lots") == []


# --- estrutura de `bids` ---


def test_bids_has_the_agreed_columns_types_and_no_defaults(db_engine: Engine) -> None:
    inspector = inspect(db_engine)
    columns = {c["name"]: c for c in inspector.get_columns("bids")}
    with db_engine.connect() as connection:
        types = dict(
            connection.execute(
                text(
                    "SELECT column_name, data_type FROM information_schema.columns "
                    "WHERE table_name = 'bids' AND table_schema = 'public'"
                )
            ).all()
        )

    assert list(columns) == BID_COLUMNS
    assert all(column["nullable"] is False for column in columns.values())
    # Sem default: `placed_at` é o instante do passo 3, nunca gerado pelo banco.
    assert all(column["default"] is None for column in columns.values())
    assert types == {
        "lot_id": "uuid",
        "sequence": "bigint",
        "bidder_id": "uuid",
        "bidder_alias": "text",
        "amount_cents": "bigint",
        "placed_at": "timestamp with time zone",
        "previous_hash": "text",
        "current_hash": "text",
        "canonical_version": "smallint",
    }


def test_bids_constraint_names_and_keys_are_exact(db_engine: Engine) -> None:
    inspector = inspect(db_engine)

    pk = inspector.get_pk_constraint("bids")
    assert (pk["name"], pk["constrained_columns"]) == (
        "pk_bids",
        ["lot_id", "sequence"],
    )
    (unique,) = inspector.get_unique_constraints("bids")
    assert unique["name"] == "uq_bids_lot_id_previous_hash"
    assert unique["column_names"] == ["lot_id", "previous_hash"]
    assert sorted(c["name"] for c in inspector.get_check_constraints("bids")) == [
        "ck_bids_amount_range",
        "ck_bids_bidder_alias_format",
        "ck_bids_canonical_version",
        "ck_bids_current_hash_format",
        "ck_bids_previous_hash_format",
        "ck_bids_sequence_positive",
    ]
    foreign_keys = {fk["name"]: fk for fk in inspector.get_foreign_keys("bids")}
    assert sorted(foreign_keys) == ["fk_bids_bidder_id_users", "fk_bids_lot_id_lots"]
    for name, table, column in (
        ("fk_bids_lot_id_lots", "lots", "lot_id"),
        ("fk_bids_bidder_id_users", "users", "bidder_id"),
    ):
        assert foreign_keys[name]["referred_table"] == table
        assert foreign_keys[name]["constrained_columns"] == [column]
        assert foreign_keys[name]["options"].get("ondelete") == "RESTRICT"
    # Nenhum índice além dos da PK e da UNIQUE (sem UUID substituto, sem índice extra).
    assert {i["name"] for i in inspector.get_indexes("bids")} <= {
        "uq_bids_lot_id_previous_hash"
    }


def test_check_literals_match_the_application_constants(db_engine: Engine) -> None:
    with db_engine.connect() as connection:
        definitions = dict(
            connection.execute(
                text(
                    "SELECT conname, pg_get_constraintdef(oid) FROM pg_constraint "
                    "WHERE conname IN ('ck_lots_current_bid_range', "
                    "'ck_bids_amount_range', 'ck_lots_empty_lot_is_genesis')"
                )
            ).all()
        )
    assert MAX_CENTS == 2**53 - 1 == 9007199254740991
    assert str(MAX_CENTS) in definitions["ck_lots_current_bid_range"]
    assert str(MAX_CENTS) in definitions["ck_bids_amount_range"]
    assert GENESIS_HASH in definitions["ck_lots_empty_lot_is_genesis"]


# --- cada CHECK de `lots` recusa pelo nome ---

# Cada linha viola uma única CHECK (o PostgreSQL as avalia em ordem alfabética).
LEADER = "LEADER"
LOT_VIOLATIONS = [
    pytest.param(
        {
            "current_bid_cents": MAX_CENTS + 1,
            "current_leader_id": LEADER,
            "bid_count": 1,
        },
        "ck_lots_current_bid_range",
        id="current-bid-above-max",
    ),
    pytest.param(
        {"current_bid_cents": 9999, "current_leader_id": LEADER, "bid_count": 1},
        "ck_lots_current_bid_at_least_starting",
        id="current-bid-below-starting",
    ),
    pytest.param(
        {"current_bid_cents": 10000, "current_leader_id": None, "bid_count": 1},
        "ck_lots_current_bid_with_leader",
        id="bid-without-leader",
    ),
    pytest.param(
        {"current_bid_cents": None, "current_leader_id": LEADER, "bid_count": 0},
        "ck_lots_current_bid_with_leader",
        id="leader-without-bid",
    ),
    pytest.param(
        {"current_bid_cents": None, "current_leader_id": None, "bid_count": 1},
        "ck_lots_bid_count_matches_current_bid",
        id="count-without-bid",
    ),
    pytest.param(
        {"current_bid_cents": 10000, "current_leader_id": LEADER, "bid_count": 0},
        "ck_lots_bid_count_matches_current_bid",
        id="bid-without-count",
    ),
    pytest.param(
        {"current_bid_cents": 10000, "current_leader_id": LEADER, "bid_count": -1},
        "ck_lots_bid_count_non_negative",
        id="negative-count",
    ),
    pytest.param(
        {
            "current_bid_cents": 10000,
            "current_leader_id": LEADER,
            "bid_count": 1,
            "final_hash": "G" * 64,
        },
        "ck_lots_final_hash_format",
        id="final-hash-not-hex",
    ),
    pytest.param(
        {
            "current_bid_cents": 10000,
            "current_leader_id": LEADER,
            "bid_count": 1,
            "final_hash": HASH_A.upper(),
        },
        "ck_lots_final_hash_format",
        id="final-hash-uppercase",
    ),
    pytest.param(
        {"final_hash": HASH_A},
        "ck_lots_empty_lot_is_genesis",
        id="empty-lot-without-genesis",
    ),
    pytest.param(
        {"anchor_hmac": "xyz"}, "ck_lots_anchor_hmac_format", id="anchor-not-hex"
    ),
    pytest.param(
        {"anchor_hmac": HASH_A.upper()},
        "ck_lots_anchor_hmac_format",
        id="anchor-uppercase",
    ),
    pytest.param(
        {"anchor_hmac": "a" * 63}, "ck_lots_anchor_hmac_format", id="anchor-short"
    ),
]


@pytest.mark.parametrize(("columns", "constraint"), LOT_VIOLATIONS)
def test_each_lot_check_refuses_by_name(
    seeded: sessionmaker[Session],
    bidder: uuid.UUID,
    columns: dict[str, Any],
    constraint: str,
) -> None:
    columns = {k: (bidder if v == LEADER else v) for k, v in columns.items()}

    with pytest.raises(IntegrityError) as error:
        lot_with(seeded, **columns)

    assert constraint in constraint_of(error)


def test_valid_lot_states_are_accepted(
    seeded: sessionmaker[Session], bidder: uuid.UUID
) -> None:
    lot_with(seeded)  # legado: zero lances, genesis, sem âncora
    lot_with(seeded, anchor_hmac=HASH_B)  # vazio assinado
    lot_with(  # um lance no limite inferior
        seeded,
        current_bid_cents=10000,
        current_leader_id=bidder,
        bid_count=1,
        final_hash=HASH_A,
        anchor_hmac=HASH_B,
    )
    lot_with(  # no limite superior
        seeded,
        starting_bid_cents=MAX_CENTS,
        current_bid_cents=MAX_CENTS,
        current_leader_id=bidder,
        bid_count=1,
        final_hash=HASH_A,
        anchor_hmac=HASH_B,
    )


def test_a_lot_cannot_be_led_by_an_unknown_user(seeded: sessionmaker[Session]) -> None:
    with pytest.raises(IntegrityError) as error:
        lot_with(
            seeded,
            current_bid_cents=10000,
            current_leader_id=uuid.uuid4(),
            bid_count=1,
            final_hash=HASH_A,
        )
    assert "fk_lots_current_leader_id_users" in constraint_of(error)


def test_a_user_that_leads_a_lot_cannot_be_deleted(
    seeded: sessionmaker[Session], bidder: uuid.UUID
) -> None:
    lot_with(
        seeded,
        current_bid_cents=10000,
        current_leader_id=bidder,
        bid_count=1,
        final_hash=HASH_A,
    )
    with pytest.raises(IntegrityError) as error:
        with seeded() as session:
            session.execute(
                text("DELETE FROM wallets WHERE user_id = :id"), {"id": bidder}
            )
            session.execute(text("DELETE FROM users WHERE id = :id"), {"id": bidder})
            session.commit()
    assert "fk_lots_current_leader_id_users" in constraint_of(error)


# --- cada CHECK, PK, UNIQUE e FK de `bids` ---


@pytest.mark.parametrize(
    ("overrides", "constraint"),
    [
        ({"sequence": 0}, "ck_bids_sequence_positive"),
        ({"sequence": -1}, "ck_bids_sequence_positive"),
        ({"amount_cents": 0}, "ck_bids_amount_range"),
        ({"amount_cents": -1}, "ck_bids_amount_range"),
        ({"amount_cents": MAX_CENTS + 1}, "ck_bids_amount_range"),
        ({"bidder_alias": "Licitante-0123456789abcdef"}, "ck_bids_bidder_alias_format"),
        ({"bidder_alias": "Licitante-0123"}, "ck_bids_bidder_alias_format"),
        ({"bidder_alias": "Anon-0123456789ABCDEF"}, "ck_bids_bidder_alias_format"),
        ({"previous_hash": HASH_A.upper()}, "ck_bids_previous_hash_format"),
        ({"previous_hash": "a" * 63}, "ck_bids_previous_hash_format"),
        ({"current_hash": "z" * 64}, "ck_bids_current_hash_format"),
        ({"current_hash": "a" * 65}, "ck_bids_current_hash_format"),
        ({"canonical_version": 2}, "ck_bids_canonical_version"),
        ({"canonical_version": 0}, "ck_bids_canonical_version"),
    ],
)
def test_each_bid_check_refuses_by_name(
    seeded: sessionmaker[Session],
    bidder: uuid.UUID,
    overrides: dict[str, Any],
    constraint: str,
) -> None:
    lot_id = lot_with(seeded)

    with pytest.raises(IntegrityError) as error:
        insert_bid(seeded, bid_values(lot_id, bidder, **overrides))

    assert constraint in constraint_of(error)


def test_the_bounds_of_a_bid_are_accepted(
    seeded: sessionmaker[Session], bidder: uuid.UUID
) -> None:
    lot_id = lot_with(seeded)
    insert_bid(seeded, bid_values(lot_id, bidder, amount_cents=1))
    insert_bid(
        seeded,
        bid_values(
            lot_id, bidder, sequence=2, amount_cents=MAX_CENTS, previous_hash=HASH_A
        ),
    )
    assert [row["amount_cents"] for row in bid_rows(seeded, lot_id)] == [1, MAX_CENTS]


def test_a_sequence_cannot_repeat_in_a_lot_but_can_in_another(
    seeded: sessionmaker[Session], bidder: uuid.UUID
) -> None:
    lot_id, other = lot_with(seeded), lot_with(seeded)
    insert_bid(seeded, bid_values(lot_id, bidder))

    with pytest.raises(IntegrityError) as error:
        insert_bid(seeded, bid_values(lot_id, bidder, previous_hash=HASH_B))
    assert "pk_bids" in constraint_of(error)

    insert_bid(seeded, bid_values(other, bidder))  # mesma sequência em outro lote


def test_a_lot_cannot_fork_two_children_of_the_same_predecessor(
    seeded: sessionmaker[Session], bidder: uuid.UUID
) -> None:
    lot_id = lot_with(seeded)
    insert_bid(seeded, bid_values(lot_id, bidder))

    with pytest.raises(IntegrityError) as error:
        insert_bid(seeded, bid_values(lot_id, bidder, sequence=2, current_hash=HASH_B))

    assert "uq_bids_lot_id_previous_hash" in constraint_of(error)


def test_bid_foreign_keys_refuse_unknown_lots_and_users(
    seeded: sessionmaker[Session], bidder: uuid.UUID
) -> None:
    lot_id = lot_with(seeded)
    with pytest.raises(IntegrityError) as error:
        insert_bid(seeded, bid_values(uuid.uuid4(), bidder))
    assert "fk_bids_lot_id_lots" in constraint_of(error)
    with pytest.raises(IntegrityError) as error:
        insert_bid(seeded, bid_values(lot_id, uuid.uuid4()))
    assert "fk_bids_bidder_id_users" in constraint_of(error)


def test_a_lot_or_a_user_with_bids_cannot_be_deleted(
    seeded: sessionmaker[Session], bidder: uuid.UUID
) -> None:
    lot_id = lot_with(seeded)
    insert_bid(seeded, bid_values(lot_id, bidder))

    with pytest.raises(IntegrityError) as error:
        with seeded() as session:
            session.execute(text("DELETE FROM lots WHERE id = :id"), {"id": lot_id})
            session.commit()
    assert "fk_bids_lot_id_lots" in constraint_of(error)
    with pytest.raises(IntegrityError) as error:
        with seeded() as session:
            session.execute(
                text("DELETE FROM wallets WHERE user_id = :id"), {"id": bidder}
            )
            session.execute(text("DELETE FROM users WHERE id = :id"), {"id": bidder})
            session.commit()
    assert "fk_bids_bidder_id_users" in constraint_of(error)


def test_placed_at_keeps_microseconds(
    seeded: sessionmaker[Session], bidder: uuid.UUID
) -> None:
    lot_id = lot_with(seeded)
    moment = NOW.replace(microsecond=123456)

    insert_bid(seeded, bid_values(lot_id, bidder, placed_at=moment))

    assert bid_rows(seeded, lot_id)[0]["placed_at"] == moment


# --- backfill e downgrade ---


@pytest.fixture
def back_at_head(test_database_url: str, db_engine: Engine) -> Iterator[None]:
    yield
    command.upgrade(alembic_config(test_database_url), "head")
    db_engine.dispose()


INSERT_OLD_LOT = text(
    "INSERT INTO lots (id, auctioneer_id, external_id, image_id, source_url, "
    "starting_bid_cents, min_increment_cents, starts_at, ends_at, created_at) "
    "VALUES (:id, :auctioneer_id, 27992, :image_id, 'https://www.artic.edu/x', "
    "10000, 1000, :starts_at, :ends_at, :created_at)"
)


def test_existing_lots_become_valid_unauthenticated_empty_lots(
    test_database_url: str,
    db_engine: Engine,
    seeded: sessionmaker[Session],
    back_at_head: None,
) -> None:
    config = alembic_config(test_database_url)
    command.downgrade(config, "0004")
    db_engine.dispose()
    old = [uuid.uuid4(), uuid.uuid4()]
    with db_engine.begin() as connection:
        for lot_id in old:
            connection.execute(
                INSERT_OLD_LOT,
                {
                    "id": lot_id,
                    "auctioneer_id": DEMO_AUCTIONEER_ID,
                    "image_id": IMAGE_ID,
                    "starts_at": NOW,
                    "ends_at": NOW + timedelta(days=1),
                    "created_at": NOW,
                },
            )

    command.upgrade(config, "head")
    db_engine.dispose()

    for lot_id in old:
        lot = lot_state(seeded, lot_id)
        assert lot["bid_count"] == 0
        assert lot["final_hash"] == GENESIS_HASH
        assert lot["current_bid_cents"] is None
        assert lot["current_leader_id"] is None
        # Estruturalmente válido, mas não autenticado: a migration não assina nada.
        assert lot["anchor_hmac"] is None
        assert lot["starting_bid_cents"] == 10000


def test_downgrade_removes_only_what_the_migration_created(
    test_database_url: str,
    db_engine: Engine,
    seeded: sessionmaker[Session],
    back_at_head: None,
) -> None:
    config = alembic_config(test_database_url)
    kept = lot_with(seeded)

    command.downgrade(config, "0004")
    db_engine.dispose()

    inspector = inspect(db_engine)
    assert "bids" not in inspector.get_table_names()
    assert {"lots", "users", "wallets"} <= set(inspector.get_table_names())
    assert [c["name"] for c in inspector.get_columns("lots")] == LOT_COLUMNS[:-6]
    assert sorted(c["name"] for c in inspector.get_check_constraints("lots")) == [
        "ck_lots_ends_after_starts",
        "ck_lots_external_id_positive",
        "ck_lots_image_id_format",
        "ck_lots_min_increment_range",
        "ck_lots_starting_bid_range",
    ]
    assert [fk["name"] for fk in inspector.get_foreign_keys("lots")] == [
        "fk_lots_auctioneer_id_users"
    ]
    with db_engine.connect() as connection:
        survivors = connection.execute(text("SELECT id FROM lots")).scalars().all()
    assert survivors == [kept]  # o lote (e a carteira) sobrevivem ao downgrade

    command.upgrade(config, "head")
    db_engine.dispose()
    assert "bids" in inspect(db_engine).get_table_names()
