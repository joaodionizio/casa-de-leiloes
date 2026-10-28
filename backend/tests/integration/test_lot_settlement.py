"""Story 4.3 PG01–03/08–16/22–34: durable economics and authenticated retry."""

import dataclasses
import uuid
from datetime import timedelta

import pytest
from sqlalchemy import event, inspect, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, sessionmaker

from app import lot_settlement as settlement
from app.bid_integrity import GENESIS_HASH
from app.bids import IntegrityConflict, IntegrityFailure, PlacedBid
from app.lot_cancellation import cancel_lot
from app.money import MAX_CENTS
from app.seed import DEMO_AUCTIONEER_ID
from app.wallet import MissingWalletError
from tests.bid_support import (
    assert_authenticated,
    bid_rows,
    integrity,
    live_lot,
    lot_state,
    run_bid,
    statement_log,
    tamper,
)
from tests.lot_support import empty_anchor
from tests.settlement_support import (
    ALICE,
    BOB,
    counts,
    expire,
    run_settle,
    snapshot,
    sold_lot,
)
from tests.settlement_support import (
    seeded as seeded,  # noqa: F401
)
from tests.wallet_support import delete_wallet, set_wallet, wallet_row, wallet_rows


def assert_conflict_without_writes(factory, engine, lot_id):
    before = snapshot(factory)
    with statement_log(engine) as log:
        result = run_settle(factory, lot_id)
    assert isinstance(result, IntegrityConflict), result
    assert not any(
        s.upper().startswith(("INSERT", "UPDATE", "DELETE")) for s in log.statements
    )
    assert snapshot(factory) == before
    return result


def test_pg01_25_28_sold_consumes_reserved_funds_once(seeded):
    set_wallet(seeded, ALICE, 50_000)
    set_wallet(seeded, DEMO_AUCTIONEER_ID, 5_000)
    lot_id = sold_lot(seeded)
    before = wallet_rows(seeded)
    result = run_settle(seeded, lot_id)
    assert result.status == "settled_sold" and result.transitioned is True
    assert wallet_row(seeded, ALICE) == (38_000, 0)
    assert 38_000 - 0 == 50_000 - 12_000
    assert wallet_row(seeded, DEMO_AUCTIONEER_ID) == (17_000, 0)
    assert sum(r[1] for r in wallet_rows(seeded)) == sum(r[1] for r in before)
    assert counts(seeded, lot_id) == (1, 1)
    s, r = result.settlement, result.receipt
    last = bid_rows(seeded, lot_id)[-1]
    assert isinstance(s.id, uuid.UUID) and isinstance(r.id, uuid.UUID)
    assert s.id != r.id and s.id != lot_id
    assert s.winner_user_id == ALICE
    assert s.anchor_hmac == lot_state(seeded, lot_id)["anchor_hmac"]
    assert r.settlement_id == s.id
    for name in (
        "lot_id",
        "winning_bid_sequence",
        "winner_alias",
        "final_amount_cents",
        "settled_at",
        "bid_count",
        "final_hash",
    ):
        assert getattr(s, name) == getattr(r, name)
    assert s.winning_bid_sequence == last["sequence"] == s.bid_count
    assert s.winner_alias == last["bidder_alias"]
    assert s.final_amount_cents == last["amount_cents"]
    assert s.final_hash == last["current_hash"]
    with seeded() as reader:
        assert settlement.read_settlement(reader, lot_id) == s
        assert settlement.read_receipt(reader, lot_id) == r


def test_pg02_27_unsold_has_authoritative_record_without_receipt(seeded, db_engine):
    lot_id = live_lot(seeded)
    expire(seeded, lot_id)
    before_wallets = wallet_rows(seeded)
    result = run_settle(seeded, lot_id)
    assert result.status == "settled_unsold" and result.transitioned
    s = result.settlement
    assert s.outcome == "unsold" and s.bid_count == 0 and s.final_hash == GENESIS_HASH
    assert (
        s.winner_user_id,
        s.winner_alias,
        s.winning_bid_sequence,
        s.final_amount_cents,
    ) == (None, None, None, None)
    assert result.receipt is None and counts(seeded, lot_id) == (1, 0)
    assert wallet_rows(seeded) == before_wallets
    with statement_log(db_engine) as log:
        repeated = run_settle(seeded, lot_id)
    assert repeated.status == "already_settled" and not repeated.transitioned
    assert repeated.settlement == s and repeated.receipt is None
    assert counts(seeded, lot_id) == (1, 0)
    assert not any(
        s.upper().startswith(("INSERT", "UPDATE", "DELETE")) for s in log.statements
    )


@pytest.mark.parametrize("scheduled", [False, True])
def test_pg03_not_due_locks_then_reads_clock_without_writes(
    seeded, db_engine, scheduled
):
    lot_id = live_lot(seeded)
    if scheduled:
        tamper(
            seeded,
            "UPDATE lots SET starts_at=ends_at-interval '1 minute' WHERE id=:id",
            id=lot_id,
        )
    before = snapshot(seeded)
    with statement_log(db_engine) as log:
        result = run_settle(seeded, lot_id)
    assert result.status == "not_due" and not result.transitioned
    assert result.settlement is result.receipt is None
    assert snapshot(seeded) == before
    lock_index = next(
        i for i, s in enumerate(log.statements) if "FOR UPDATE" in s.upper()
    )
    clocks = [i for i, s in enumerate(log.statements) if "CLOCK_TIMESTAMP" in s.upper()]
    assert len(clocks) == 1 and lock_index < clocks[0]


def test_pg08_retry_preserves_originals_and_never_touches_wallets(seeded, db_engine):
    lot_id = sold_lot(seeded)
    first = run_settle(seeded, lot_id)
    # Reserve was consumed. Legitimate later deposits and commitments do not
    # become a prerequisite to revalidate the original economic record.
    set_wallet(seeded, ALICE, 1, 0)
    before = snapshot(seeded)
    with statement_log(db_engine) as log:
        second = run_settle(seeded, lot_id)
    assert second.status == "already_settled" and not second.transitioned
    assert second.settlement == first.settlement and second.receipt == first.receipt
    assert snapshot(seeded) == before
    assert not any(
        "FROM wallets" in s or s.upper().startswith(("INSERT", "UPDATE", "DELETE"))
        for s in log.statements
    )


def test_pg09_26_other_reservations_and_loser_remain_intact(seeded):
    other = live_lot(seeded, starting_bid_cents=20_000)
    assert isinstance(run_bid(seeded, other, ALICE, 20_000), PlacedBid)
    loser_other = live_lot(seeded, starting_bid_cents=7_000)
    assert isinstance(run_bid(seeded, loser_other, BOB, 7_000), PlacedBid)
    target = live_lot(seeded, starting_bid_cents=10_000, min_increment_cents=2_000)
    assert isinstance(run_bid(seeded, target, BOB, 10_000), PlacedBid)
    assert isinstance(run_bid(seeded, target, ALICE, 12_000), PlacedBid)
    expire(seeded, target)
    before = wallet_rows(seeded)
    other_before = lot_state(seeded, other)
    result = run_settle(seeded, target)
    assert result.status == "settled_sold"
    assert wallet_row(seeded, ALICE) == (68_000, 20_000)
    assert 68_000 - 20_000 == 80_000 - 32_000
    assert wallet_row(seeded, BOB) == (80_000, 7_000)
    assert lot_state(seeded, other) == other_before
    assert counts(seeded, other) == (0, 0)
    assert sum(r[1] for r in before) == sum(r[1] for r in wallet_rows(seeded))


@pytest.mark.parametrize("case", ["exact", "overflow", "insufficient", "missing"])
def test_pg10_30_financial_boundaries_are_atomic(seeded, case):
    lot_id = sold_lot(seeded, amount=10)
    if case in ("exact", "overflow"):
        set_wallet(
            seeded, DEMO_AUCTIONEER_ID, MAX_CENTS - (10 if case == "exact" else 5)
        )
    elif case == "insufficient":
        set_wallet(seeded, ALICE, 80_000, 9)
    else:
        delete_wallet(seeded, ALICE)
    before = snapshot(seeded)
    if case == "exact":
        assert run_settle(seeded, lot_id).status == "settled_sold"
        assert wallet_row(seeded, DEMO_AUCTIONEER_ID) == (MAX_CENTS, 0)
    else:
        error = (
            MissingWalletError
            if case == "missing"
            else settlement.SettlementFinancialConflict
        )
        with pytest.raises(error) as caught:
            run_settle(seeded, lot_id)
        if case != "missing":
            assert caught.value.reason == (
                "credit_limit_exceeded"
                if case == "overflow"
                else "insufficient_commitment"
            )
        assert snapshot(seeded) == before and counts(seeded, lot_id) == (0, 0)


@pytest.mark.parametrize(
    "stage",
    ["history", "wallet_first", "wallet_second", "settlement", "receipt", "precommit"],
)
def test_pg11_failure_at_each_stage_rolls_back_all_entities(seeded, db_engine, stage):
    lot_id = sold_lot(seeded)
    before = snapshot(seeded)
    hits = []

    def inject(conn, cursor, statement, parameters, context, executemany):
        sql = " ".join(statement.upper().split())
        hit = (
            (stage == "history" and sql.startswith("SELECT") and "FROM BIDS" in sql)
            or (stage.startswith("wallet") and sql.startswith("UPDATE WALLETS"))
            or (stage == "settlement" and sql.startswith("INSERT INTO LOT_SETTLEMENTS"))
            or (stage == "receipt" and sql.startswith("INSERT INTO RECEIPTS"))
        )
        if hit:
            hits.append(sql)
            if stage != "wallet_second" or len(hits) == 2:
                raise RuntimeError("synthetic stage failure")

    event.listen(db_engine, "before_cursor_execute", inject)

    class FailingCommit(Session):
        def commit(self):
            raise RuntimeError("synthetic stage failure")

    factory = (
        sessionmaker(bind=db_engine, class_=FailingCommit)
        if stage == "precommit"
        else seeded
    )
    try:
        with pytest.raises(RuntimeError, match="synthetic stage failure"):
            run_settle(factory, lot_id)
    finally:
        event.remove(db_engine, "before_cursor_execute", inject)
    assert snapshot(seeded) == before
    assert counts(seeded, lot_id) == (0, 0)
    assert run_settle(seeded, lot_id).status == "settled_sold"


@pytest.mark.parametrize(
    "mutation",
    [
        "UPDATE bids SET amount_cents=amount_cents+1 WHERE lot_id=:id AND sequence=1",
        "UPDATE bids SET current_hash=repeat('a',64) WHERE lot_id=:id AND sequence=1",
        "UPDATE lots SET anchor_hmac=repeat('a',64) WHERE id=:id",
        "UPDATE lots SET final_hash=repeat('a',64) WHERE id=:id",
        "UPDATE lots SET current_leader_id=:other WHERE id=:id",
    ],
)
def test_pg13_tampering_is_rejected_before_effects(seeded, db_engine, mutation):
    lot_id = sold_lot(seeded)
    tamper(seeded, mutation, id=lot_id, other=BOB)
    assert_conflict_without_writes(seeded, db_engine, lot_id)


@pytest.mark.parametrize("has_bids", [False, True])
@pytest.mark.parametrize("wrong_anchor", [False, True])
def test_pg14_legacy_or_wrong_lot_anchor_never_repaired(
    seeded, db_engine, has_bids, wrong_anchor
):
    lot_id = sold_lot(seeded) if has_bids else live_lot(seeded)
    expire(seeded, lot_id)
    tamper(
        seeded,
        "UPDATE lots SET anchor_hmac=:anchor WHERE id=:id",
        id=lot_id,
        anchor=empty_anchor(uuid.uuid4()) if wrong_anchor else None,
    )
    assert_conflict_without_writes(seeded, db_engine, lot_id)


@pytest.mark.parametrize("tampered", [False, True])
def test_pg15_full_history_beyond_recent_window(seeded, db_engine, tampered):
    lot_id = live_lot(seeded, starting_bid_cents=10, min_increment_cents=1)
    for index in range(55):
        result = run_bid(seeded, lot_id, ALICE if index % 2 == 0 else BOB, 10 + index)
        assert isinstance(result, PlacedBid)
    expire(seeded, lot_id)
    if tampered:
        tamper(
            seeded,
            "UPDATE bids SET amount_cents=11 WHERE lot_id=:id AND sequence=1",
            id=lot_id,
        )
        assert_conflict_without_writes(seeded, db_engine, lot_id)
    else:
        result = run_settle(seeded, lot_id)
        assert result.settlement.bid_count == 55
        assert result.receipt.winning_bid_sequence == 55
        assert result.receipt.final_hash == bid_rows(seeded, lot_id)[-1]["current_hash"]


def test_pg16_29_receipt_whitelist_schema_dto_and_logs(seeded, db_engine, caplog):
    lot_id = sold_lot(seeded)
    result = run_settle(seeded, lot_id)
    expected = {
        "id",
        "lot_id",
        "settlement_id",
        "winning_bid_sequence",
        "winner_alias",
        "final_amount_cents",
        "settled_at",
        "bid_count",
        "final_hash",
    }
    assert {f.name for f in dataclasses.fields(result.receipt)} == expected
    assert {c["name"] for c in inspect(db_engine).get_columns("receipts")} == expected
    assert {"anchor_hmac", "winner_user_id"} <= {
        f.name for f in dataclasses.fields(result.settlement)
    }
    assert not any(
        marker in caplog.text for marker in (str(ALICE), result.settlement.anchor_hmac)
    )
    with pytest.raises(dataclasses.FrozenInstanceError):
        result.receipt.final_amount_cents = 0


def test_readers_are_pure_and_missing_is_legitimate(seeded, db_engine):
    pending = live_lot(seeded)
    sold = sold_lot(seeded)
    result = run_settle(seeded, sold)
    before = snapshot(seeded)
    with statement_log(db_engine) as log, seeded() as session:
        assert settlement.read_settlement(session, pending) is None
        assert settlement.read_receipt(session, pending) is None
        assert settlement.read_settlement(session, sold) == result.settlement
        assert settlement.read_receipt(session, sold) == result.receipt
        assert settlement.read_receipt(session, uuid.uuid4()) is None
    assert snapshot(seeded) == before
    assert all(
        "FOR UPDATE" not in s.upper()
        and not s.upper().startswith(("INSERT", "UPDATE", "DELETE"))
        for s in log.statements
    )


def test_pg22_real_postgresql_commit_abort_leaves_nothing(seeded, db_engine):
    lot_id = sold_lot(seeded)
    before = snapshot(seeded)
    with db_engine.begin() as connection:
        connection.execute(
            text(
                "CREATE FUNCTION reject_test_settlement() RETURNS "
                "trigger LANGUAGE plpgsql AS $$ BEGIN RAISE EXCEPTION "
                "'synthetic deferred abort'; END $$"
            )
        )
        connection.execute(
            text(
                "CREATE CONSTRAINT TRIGGER reject_test_settlement AFTER"
                " INSERT ON lot_settlements DEFERRABLE INITIALLY "
                "DEFERRED FOR EACH ROW EXECUTE FUNCTION "
                "reject_test_settlement()"
            )
        )
    try:
        with pytest.raises(Exception, match="synthetic deferred abort"):
            run_settle(seeded, lot_id)
        assert snapshot(seeded) == before and counts(seeded, lot_id) == (0, 0)
    finally:
        with db_engine.begin() as connection:
            connection.execute(
                text("DROP TRIGGER reject_test_settlement ON lot_settlements")
            )
            connection.execute(text("DROP FUNCTION reject_test_settlement()"))
    assert run_settle(seeded, lot_id).status == "settled_sold"


def test_pg34_commit_happens_before_lost_confirmation_and_retry(seeded, db_engine):
    lot_id = sold_lot(seeded)

    class LostAcknowledgement(Session):
        def commit(self):
            super().commit()
            raise RuntimeError("synthetic lost acknowledgement")

    factory = sessionmaker(
        bind=db_engine, class_=LostAcknowledgement, expire_on_commit=False
    )
    with pytest.raises(RuntimeError, match="synthetic lost acknowledgement"):
        run_settle(factory, lot_id)
    assert counts(seeded, lot_id) == (1, 1)
    assert wallet_row(seeded, ALICE) == (68_000, 0)
    before = snapshot(seeded)
    retry = run_settle(seeded, lot_id)
    assert retry.status == "already_settled" and not retry.transitioned
    assert snapshot(seeded) == before


@pytest.mark.parametrize(
    "table,column,value",
    [
        ("lot_settlements", "settled_at", "settled_at + interval '1 second'"),
        ("receipts", "final_amount_cents", "final_amount_cents+1"),
        ("lot_settlements", "anchor_hmac", "repeat('b',64)"),
        ("bids", "amount_cents", "amount_cents+1"),
    ],
)
def test_pg23_31_inconsistent_retry_is_conflict_without_repair(
    seeded, db_engine, table, column, value
):
    lot_id = sold_lot(seeded)
    run_settle(seeded, lot_id)
    tamper(seeded, f"UPDATE {table} SET {column}={value} WHERE lot_id=:id", id=lot_id)
    if table != "bids":
        assert_authenticated(seeded, lot_id)
    assert_conflict_without_writes(seeded, db_engine, lot_id)


def test_f43_01_retry_rejects_only_tampered_winner_user_id(seeded, db_engine):
    lot_id = sold_lot(seeded)
    original = run_settle(seeded, lot_id)
    assert (
        original.status == "settled_sold"
        and original.settlement.winner_user_id == ALICE
    )
    assert counts(seeded, lot_id) == (1, 1)
    tamper(
        seeded,
        "UPDATE lot_settlements SET winner_user_id=:winner WHERE lot_id=:id",
        winner=BOB,
        id=lot_id,
    )
    assert_authenticated(seeded, lot_id)
    conflict = assert_conflict_without_writes(seeded, db_engine, lot_id)
    assert conflict.reason == IntegrityFailure.SETTLEMENT_MISMATCH
    assert counts(seeded, lot_id) == (1, 1)


def test_pg32_sold_missing_receipt_is_never_recreated(seeded, db_engine):
    lot_id = sold_lot(seeded)
    run_settle(seeded, lot_id)
    tamper(seeded, "DELETE FROM receipts WHERE lot_id=:id", id=lot_id)
    assert_authenticated(seeded, lot_id)
    assert_conflict_without_writes(seeded, db_engine, lot_id)
    assert counts(seeded, lot_id) == (1, 0)
    with seeded() as session:
        assert isinstance(settlement.read_receipt(session, lot_id), IntegrityConflict)


def test_pg33_unsold_intrusive_receipt_is_not_removed(seeded, db_engine):
    lot_id = live_lot(seeded)
    expire(seeded, lot_id)
    result = run_settle(seeded, lot_id)
    with db_engine.connect() as connection:
        fk = connection.execute(
            text(
                "SELECT conname, pg_get_constraintdef(oid) FROM "
                "pg_constraint WHERE conrelid='receipts'::regclass AND "
                "confrelid='bids'::regclass AND contype='f'"
            )
        ).one()
    with db_engine.begin() as connection:
        connection.execute(text(f'ALTER TABLE receipts DROP CONSTRAINT "{fk[0]}"'))
    try:
        tamper(
            seeded,
            "INSERT INTO receipts "
            "(id,lot_id,settlement_id,winning_bid_sequence,winner_alias,final_amount_cents,settled_at,bid_count,final_hash)"
            " VALUES "
            "(:rid,:id,:sid,1,'Licitante-AAAAAAAAAAAAAAAA',1,:at,1,:hash)",
            rid=uuid.uuid4(),
            id=lot_id,
            sid=result.settlement.id,
            at=result.settlement.settled_at,
            hash="a" * 64,
        )
        assert_authenticated(seeded, lot_id)
        assert_conflict_without_writes(seeded, db_engine, lot_id)
        assert counts(seeded, lot_id) == (1, 1)
        with seeded() as session:
            assert isinstance(
                settlement.read_receipt(session, lot_id), IntegrityConflict
            )
    finally:
        with db_engine.begin() as connection:
            connection.execute(
                text("DELETE FROM receipts WHERE lot_id=:id"), {"id": lot_id}
            )
            connection.execute(
                text(f'ALTER TABLE receipts ADD CONSTRAINT "{fk[0]}" {fk[1]}')
            )


def test_pg24_terminal_future_end_never_reopens(seeded, db_engine):
    lot_id = sold_lot(seeded)
    result = run_settle(seeded, lot_id)
    tamper(
        seeded,
        "UPDATE lots SET ends_at=:end WHERE id=:id",
        id=lot_id,
        end=result.settlement.settled_at + timedelta(hours=1),
    )
    assert_conflict_without_writes(seeded, db_engine, lot_id)
    before = snapshot(seeded)
    assert isinstance(run_bid(seeded, lot_id, BOB, 15_000), IntegrityConflict)
    assert snapshot(seeded) == before


def test_f43_02_unsold_future_end_rejects_retry_and_cancellation(seeded, db_engine):
    lot_id = live_lot(seeded)
    expire(seeded, lot_id)
    original = run_settle(seeded, lot_id)
    assert original.status == "settled_unsold" and original.transitioned
    assert original.receipt is None and counts(seeded, lot_id) == (1, 0)
    tamper(
        seeded,
        "UPDATE lots SET ends_at=:end WHERE id=:id",
        id=lot_id,
        end=original.settlement.settled_at + timedelta(hours=1),
    )
    assert_authenticated(seeded, lot_id)
    assert (
        assert_conflict_without_writes(seeded, db_engine, lot_id).reason
        == IntegrityFailure.SETTLEMENT_MISMATCH
    )
    before = snapshot(seeded)
    with statement_log(db_engine) as log, seeded() as session:
        result = cancel_lot(
            session,
            lot_id=lot_id,
            auctioneer_id=DEMO_AUCTIONEER_ID,
            integrity=integrity(),
        )
        session.rollback()
    assert result == IntegrityConflict(IntegrityFailure.SETTLEMENT_MISMATCH)
    assert not any(
        s.upper().startswith(("INSERT", "UPDATE", "DELETE")) for s in log.statements
    )
    assert snapshot(seeded) == before
    assert counts(seeded, lot_id) == (1, 0)


def test_pg12_schema_keys_types_and_foreign_keys(db_engine):
    inspector = inspect(db_engine)
    for table in ("lot_settlements", "receipts"):
        assert inspector.get_pk_constraint(table)["constrained_columns"] == ["id"]
        uniques = {
            tuple(c["column_names"]) for c in inspector.get_unique_constraints(table)
        }
        assert ("lot_id",) in uniques
        columns = {c["name"]: c for c in inspector.get_columns(table)}
        assert str(columns["winning_bid_sequence"]["type"]) == "BIGINT"
        assert columns["settled_at"]["type"].timezone
        fks = inspector.get_foreign_keys(table)
        assert any(
            fk["constrained_columns"] == ["lot_id", "winning_bid_sequence"]
            and fk["referred_table"] == "bids"
            and fk["referred_columns"] == ["lot_id", "sequence"]
            and fk["options"]["ondelete"] == "RESTRICT"
            for fk in fks
        )
    uniques = {
        tuple(c["column_names"]) for c in inspector.get_unique_constraints("receipts")
    }
    assert ("settlement_id",) in uniques
    assert any(
        fk["constrained_columns"] == ["settlement_id", "lot_id"]
        and fk["referred_table"] == "lot_settlements"
        and fk["referred_columns"] == ["id", "lot_id"]
        for fk in inspector.get_foreign_keys("receipts")
    )


@pytest.mark.parametrize(
    "table,change",
    [
        ("lot_settlements", {"id": None}),
        ("lot_settlements", {"id": "new"}),
        ("lot_settlements", {"winner_alias": None}),
        ("lot_settlements", {"winning_bid_sequence": 2, "bid_count": 2}),
        ("lot_settlements", {"outcome": "unsold"}),
        ("lot_settlements", {"final_amount_cents": 0}),
        ("receipts", {"id": "new"}),
        ("receipts", {"settlement_id": "new"}),
        ("receipts", {"lot_id": "new"}),
        ("receipts", {"winner_alias": "private"}),
        ("receipts", {"final_amount_cents": 0}),
        ("receipts", {"bid_count": 2}),
    ],
)
def test_pg12_real_constraints_reject_invalid_rows(seeded, table, change):
    lot_id = sold_lot(seeded)
    run_settle(seeded, lot_id)
    with seeded() as session:
        data = dict(
            session.execute(
                text(f"SELECT * FROM {table} WHERE lot_id=:id"), {"id": lot_id}
            )
            .one()
            ._mapping
        )
    for name, value in change.items():
        data[name] = uuid.uuid4() if value == "new" else value
    # UPDATE isolates CHECK/FK predicates from the duplicate-lot UNIQUE guard.
    if set(change) == {"id"}:
        command = (
            f"INSERT INTO {table} ({','.join(data)}) "
            f"VALUES ({','.join(':' + n for n in data)})"
        )
        parameters = data
    else:
        command = (
            f"UPDATE {table} SET {','.join(n + '=:' + n for n in change)} "
            "WHERE lot_id=:target"
        )
        parameters = {**{n: data[n] for n in change}, "target": lot_id}
    before = snapshot(seeded)
    with pytest.raises(IntegrityError), seeded() as session:
        session.execute(text(command), parameters)
        session.commit()
    assert snapshot(seeded) == before


def test_absent_lot_returns_none(seeded):
    assert run_settle(seeded, uuid.uuid4()) is None


@pytest.mark.parametrize(
    "attack", ["g2", "g4", "g6", "g11", "g12", "g13", "g19", "g20", "g21", "g22"]
)
def test_pg13_insertion_removal_truncation_rehash_and_operational_binding(
    seeded, db_engine, attack
):
    from tests.integration import test_bid_integrity_gate as gates

    lot_id = gates.chained_lot(seeded)
    expire(seeded, lot_id)

    def unexpected_ddl(*args):
        raise AssertionError("these attacks do not need to suspend constraints")

    case = gates.Case(seeded, lot_id, unexpected_ddl)
    getattr(gates, attack)(case)
    assert_conflict_without_writes(seeded, db_engine, lot_id)


@pytest.mark.parametrize(
    "offset,status", [(-1, "not_due"), (0, "settled_unsold"), (1, "settled_unsold")]
)
def test_u01_pg03_exact_end_is_due_under_real_lock(seeded, monkeypatch, offset, status):
    lot_id = live_lot(seeded)
    ends_at = lot_state(seeded, lot_id)["ends_at"]
    instant = ends_at + timedelta(microseconds=offset)
    monkeypatch.setattr(settlement, "database_now", lambda session: instant)
    result = run_settle(seeded, lot_id)
    assert result.status == status
    assert result.transitioned is (offset >= 0)
    assert counts(seeded, lot_id) == ((1, 0) if offset >= 0 else (0, 0))
    if offset >= 0:
        assert result.settlement.settled_at == instant


def test_readers_never_autoflush_dirty_caller_state(seeded, db_engine):
    from app.wallet import Wallet

    lot_id = sold_lot(seeded)
    result = run_settle(seeded, lot_id)
    before = snapshot(seeded)
    with seeded() as session:
        wallet = session.get(Wallet, ALICE)
        wallet.total_balance_cents += 1
        assert session.dirty
        with statement_log(db_engine) as log:
            assert settlement.read_settlement(session, lot_id) == result.settlement
            assert settlement.read_receipt(session, lot_id) == result.receipt
        assert not any(
            sql.upper().startswith(("INSERT", "UPDATE", "DELETE"))
            or "FOR UPDATE" in sql.upper()
            for sql in log.statements
        )
        session.rollback()
    assert snapshot(seeded) == before
