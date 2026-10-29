"""Cancelamento do lote sobre PostgreSQL real (Story 3.6; AD-6, AD-7, AD-8, AD-11).

O caminho de ação passa pelo serviço e pela rota reais; SQL direto é só preparo e
adulteração do banco de teste. A concorrência está em
`test_lot_cancellation_concurrency.py`."""

import uuid
from datetime import datetime, timedelta
from typing import Any

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

from app import lot_cancellation
from app.bid_integrity import GENESIS_HASH
from app.bids import PlacedBid
from app.lot_cancellation import CancellationRefusal, CancelledLot
from app.security import hash_password
from app.seed import DEMO_AUCTIONEER_ID, DEMO_PASSWORD
from tests.auth_support import (
    AUCTIONEER_EMAIL,
    BIDDER_EMAIL,
    HTTPS_ORIGIN,
    build_client,
    json_headers,
    login,
    seeded_id,
)
from tests.bid_support import (
    assert_authenticated,
    assert_invariants,
    bid_rows,
    db_snapshot,
    integrity,
    live_lot,
    locked_wallet_ids,
    lot_state,
    lot_update_columns,
    run_bid,
    service_trace,
    statement_log,
    tamper,
)
from tests.cancel_support import run_cancel, untouched
from tests.lot_support import db_now, empty_anchor, insert_lot, statement_recorder
from tests.wallet_support import seed_users_with_wallets, set_wallet

ALICE = seeded_id(BIDDER_EMAIL)
OTHER_AUCTIONEER_EMAIL = "outro-leiloeiro@example.com"
INTEGRITY_BODY = {
    "status": 409,
    "code": "lot_integrity_conflict",
    "message": "Não foi possível concluir a operação porque a integridade do lote "
    "não pôde ser confirmada.",
}


@pytest.fixture
def seeded(
    db_session_factory: sessionmaker[Session], clean_users: None
) -> sessionmaker[Session]:
    seed_users_with_wallets(db_session_factory)
    set_wallet(db_session_factory, ALICE, 1_000_000)
    return db_session_factory


def client_as(
    monkeypatch: pytest.MonkeyPatch,
    factory: sessionmaker[Session],
    email: str | None,
    *,
    raise_server_exceptions: bool = True,
) -> TestClient:
    client = build_client(monkeypatch, HTTPS_ORIGIN, session_factory=factory)
    client = TestClient(
        client.app,
        base_url=HTTPS_ORIGIN,
        raise_server_exceptions=raise_server_exceptions,
    )
    if email is not None:
        assert login(client, HTTPS_ORIGIN, email).status_code == 200
    return client


@pytest.fixture
def auctioneer(
    monkeypatch: pytest.MonkeyPatch, seeded: sessionmaker[Session]
) -> TestClient:
    return client_as(monkeypatch, seeded, AUCTIONEER_EMAIL)


@pytest.fixture
def bidder(
    monkeypatch: pytest.MonkeyPatch, seeded: sessionmaker[Session]
) -> TestClient:
    return client_as(monkeypatch, seeded, BIDDER_EMAIL)


@pytest.fixture
def anonymous(
    monkeypatch: pytest.MonkeyPatch, seeded: sessionmaker[Session]
) -> TestClient:
    return client_as(monkeypatch, seeded, None)


def add_other_auctioneer(factory: sessionmaker[Session]) -> uuid.UUID:
    other = uuid.uuid4()
    with factory() as session:
        session.execute(
            text(
                "INSERT INTO users (id, email, password_hash, role) "
                "VALUES (:id, :email, :hash, 'AUCTIONEER')"
            ),
            {
                "id": other,
                "email": OTHER_AUCTIONEER_EMAIL,
                "hash": hash_password(DEMO_PASSWORD),
            },
        )
        session.commit()
    return other


def cancel(client: TestClient, lot_id: Any) -> Any:
    return client.post(f"/api/lots/{lot_id}/cancel", headers=json_headers(HTTPS_ORIGIN))


def scheduled_lot(factory: sessionmaker[Session]) -> uuid.UUID:
    now = db_now(factory)
    return live_lot(
        factory, starts_at=now + timedelta(hours=1), ends_at=now + timedelta(hours=3)
    )


def ended_lot(factory: sessionmaker[Session]) -> uuid.UUID:
    now = db_now(factory)
    return live_lot(
        factory, starts_at=now - timedelta(hours=3), ends_at=now - timedelta(hours=1)
    )


def parse(moment: str) -> datetime:
    return datetime.fromisoformat(moment)


def lot_with_bid(factory: sessionmaker[Session]) -> uuid.UUID:
    lot_id = live_lot(factory, starting_bid_cents=10_000)
    assert isinstance(run_bid(factory, lot_id, ALICE, 10_000), PlacedBid)
    return lot_id


def assert_integrity_conflict(response: Any) -> None:
    assert response.status_code == 409
    assert response.json() == INTEGRITY_BODY
    for word in ("lance", "hash", "HMAC", "âncora", "cadeia"):
        assert word not in response.json()["message"]


# --- sucesso (I01, I02, I13, I14) ---


@pytest.mark.parametrize("scheduled", [False, True], ids=["live", "scheduled"])
def test_the_owner_cancels_an_empty_lot_and_only_cancelled_at_changes(
    auctioneer: TestClient, seeded: sessionmaker[Session], scheduled: bool
) -> None:
    lot_id = scheduled_lot(seeded) if scheduled else live_lot(seeded)
    set_wallet(seeded, ALICE, 50_000, 7_000)
    before = untouched(seeded, lot_id)
    started = db_now(seeded)

    response = cancel(auctioneer, lot_id)

    finished = db_now(seeded)
    assert response.status_code == 200
    assert response.headers["cache-control"] == "no-store"
    body = response.json()
    assert sorted(body) == ["cancelled_at", "id"]
    assert body["id"] == str(lot_id)
    stored = lot_state(seeded, lot_id)["cancelled_at"]
    assert stored is not None and started <= stored <= finished
    assert parse(body["cancelled_at"]) == stored
    # Nada além de `cancelled_at`: lote, lances (nenhum) e todas as carteiras.
    assert untouched(seeded, lot_id) == before
    assert bid_rows(seeded, lot_id) == []
    assert_authenticated(seeded, lot_id)  # a âncora original continua válida


def test_the_persisted_instant_is_the_single_one_database_now_returned(
    monkeypatch: pytest.MonkeyPatch, seeded: sessionmaker[Session]
) -> None:
    seen: list[datetime] = []
    real = lot_cancellation.database_now

    def spy(session: Session) -> datetime:
        seen.append(real(session))
        return seen[-1]

    monkeypatch.setattr(lot_cancellation, "database_now", spy)
    lot_id = live_lot(seeded)

    result = run_cancel(seeded, lot_id)

    assert isinstance(result, CancelledLot)
    assert len(seen) == 1  # um instante por operação
    assert result.cancelled_at == seen[0]
    assert lot_state(seeded, lot_id)["cancelled_at"] == seen[0]


def test_the_statement_order_is_lock_clock_history_one_lot_update_and_no_wallet(
    seeded: sessionmaker[Session], db_engine: Engine
) -> None:
    lot_id = live_lot(seeded)

    with statement_log(db_engine) as log:
        result = run_cancel(seeded, lot_id)

    assert isinstance(result, CancelledLot)
    assert service_trace(log) == ["lock_lot", "clock", "history", "update_lot"]
    assert lot_update_columns(log) == ["cancelled_at"]
    assert locked_wallet_ids(log) == []
    assert not log.saw("wallets")  # nem trava, nem leitura, nem escrita
    assert not log.saw("INSERT INTO") and not log.saw("DELETE")


# --- política, dono, entrada (I05 a I07) ---


def test_another_auctioneer_gets_403_and_the_gate_does_not_even_run(
    monkeypatch: pytest.MonkeyPatch, seeded: sessionmaker[Session]
) -> None:
    add_other_auctioneer(seeded)
    other = client_as(monkeypatch, seeded, OTHER_AUCTIONEER_EMAIL)
    lot_id = live_lot(seeded)
    tamper(
        seeded, "UPDATE lots SET anchor_hmac = :h WHERE id = :id", h="a" * 64, id=lot_id
    )
    gate_calls: list[Any] = []
    real = lot_cancellation.authenticate_previous_state
    monkeypatch.setattr(
        lot_cancellation,
        "authenticate_previous_state",
        lambda *a, **k: gate_calls.append(1) or real(*a, **k),
    )
    before = db_snapshot(seeded)

    response = cancel(other, lot_id)

    assert response.status_code == 403
    assert response.json()["code"] == "forbidden"
    assert gate_calls == []  # o dono vem antes: não expõe a integridade do alheio
    assert db_snapshot(seeded) == before


def test_another_auctioneer_cannot_even_re_cancel(
    monkeypatch: pytest.MonkeyPatch,
    auctioneer: TestClient,
    seeded: sessionmaker[Session],
) -> None:
    add_other_auctioneer(seeded)
    other = client_as(monkeypatch, seeded, OTHER_AUCTIONEER_EMAIL)
    lot_id = live_lot(seeded)
    assert cancel(auctioneer, lot_id).status_code == 200

    assert cancel(other, lot_id).status_code == 403


def test_bidder_gets_403_and_anonymous_gets_401_with_no_effect(
    bidder: TestClient, anonymous: TestClient, seeded: sessionmaker[Session]
) -> None:
    lot_id = live_lot(seeded)
    before = db_snapshot(seeded)

    assert cancel(bidder, lot_id).status_code == 403
    assert cancel(anonymous, lot_id).status_code == 401
    # A política vem antes da validação do path e da existência.
    assert cancel(bidder, "nao-e-uuid").status_code == 403
    assert cancel(anonymous, "nao-e-uuid").status_code == 401
    assert cancel(bidder, uuid.uuid4()).status_code == 403
    assert db_snapshot(seeded) == before


def test_csrf_guard_is_inherited_without_a_body(
    auctioneer: TestClient, seeded: sessionmaker[Session]
) -> None:
    lot_id = live_lot(seeded)
    before = db_snapshot(seeded)
    url = f"/api/lots/{lot_id}/cancel"

    wrong_origin = auctioneer.post(
        url,
        headers={"Origin": "https://evil.example", "Content-Type": "application/json"},
    )
    no_origin = auctioneer.post(url, headers={"Content-Type": "application/json"})
    no_content_type = auctioneer.post(url, headers={"Origin": HTTPS_ORIGIN})

    assert wrong_origin.status_code == 403
    assert no_origin.status_code == 403
    assert no_content_type.status_code == 415
    assert db_snapshot(seeded) == before


def test_missing_lot_is_404_and_a_malformed_id_is_422_for_the_auctioneer(
    auctioneer: TestClient,
) -> None:
    missing = cancel(auctioneer, uuid.uuid4())
    malformed = cancel(auctioneer, "nao-e-uuid")

    assert (missing.status_code, missing.json()["code"]) == (404, "not_found")
    assert (malformed.status_code, malformed.json()["code"]) == (
        422,
        "validation_error",
    )
    assert malformed.json()["details"] == [
        {"loc": ["path", "lot_id"], "type": "uuid_parsing"}
    ]


# --- lances e fim (I03, I04) ---


@pytest.mark.parametrize("scheduled", [False, True], ids=["live", "scheduled-history"])
def test_cancelling_bids_releases_only_current_reservation_and_preserves_audit(
    auctioneer: TestClient,
    anonymous: TestClient,
    bidder: TestClient,
    seeded: sessionmaker[Session],
    db_engine: Engine,
    scheduled: bool,
) -> None:
    from tests.bid_support import add_bidder
    from tests.wallet_support import wallet_row

    other = live_lot(seeded, starting_bid_cents=7_000)
    assert isinstance(run_bid(seeded, other, ALICE, 7_000), PlacedBid)
    lot_id = lot_with_bid(seeded)
    bob = add_bidder(seeded, 100_000)
    assert isinstance(run_bid(seeded, lot_id, bob, 11_000), PlacedBid)
    assert isinstance(run_bid(seeded, lot_id, ALICE, 12_000), PlacedBid)
    if scheduled:
        now = db_now(seeded)
        tamper(
            seeded,
            "UPDATE lots SET starts_at=:s, ends_at=:e WHERE id=:id",
            s=now + timedelta(hours=1),
            e=now + timedelta(hours=2),
            id=lot_id,
        )
    before = lot_state(seeded, lot_id)
    history = bid_rows(seeded, lot_id)
    total, committed = wallet_row(seeded, ALICE)
    with statement_log(db_engine) as log:
        response = cancel(auctioneer, lot_id)
    assert response.status_code == 200
    assert locked_wallet_ids(log) == [ALICE]
    after = lot_state(seeded, lot_id)
    assert after.pop("cancelled_at") is not None
    before.pop("cancelled_at")
    assert after == before
    assert bid_rows(seeded, lot_id) == history
    assert wallet_row(seeded, ALICE) == (total, committed - 12_000)
    assert wallet_row(seeded, ALICE) == (1_000_000, 7_000)
    assert wallet_row(seeded, bob) == (100_000, 0)
    wallet = bidder.get("/api/wallet").json()
    assert wallet["available_balance_cents"] == total - 7_000
    audit = anonymous.get(f"/api/lots/{lot_id}/audit").json()
    assert audit["integrity"] == "verified" and audit["phase"] == "cancelled"
    assert audit["bid_count"] == 3 and len(audit["bids"]) == 3
    assert (
        audit["settlement_status"] == "not_applicable" and audit["settlement"] is None
    )
    assert str(lot_id) not in anonymous.get("/api/lots").text
    first_snapshot = db_snapshot(seeded)
    with statement_recorder(db_engine) as recorder:
        repeat = cancel(auctioneer, lot_id)
    assert repeat.json() == response.json()
    assert db_snapshot(seeded) == first_snapshot
    assert not any(
        s.lstrip().upper().startswith(("UPDATE", "INSERT", "DELETE"))
        for s in recorder.statements
    )
    assert_authenticated(seeded, lot_id)
    assert_invariants(seeded)


def test_a_lot_with_a_bid_that_also_ended_is_lot_ended(
    auctioneer: TestClient, seeded: sessionmaker[Session]
) -> None:
    lot_id = lot_with_bid(seeded)
    now = db_now(seeded)
    tamper(
        seeded,
        "UPDATE lots SET starts_at = :s, ends_at = :e WHERE id = :id",
        s=now - timedelta(hours=3),
        e=now - timedelta(hours=1),
        id=lot_id,
    )

    assert cancel(auctioneer, lot_id).json()["code"] == "lot_ended"


def test_an_ended_lot_without_bids_is_422_lot_ended_with_no_effect(
    auctioneer: TestClient, seeded: sessionmaker[Session]
) -> None:
    lot_id = ended_lot(seeded)
    before = db_snapshot(seeded)

    response = cancel(auctioneer, lot_id)

    assert response.status_code == 422
    assert response.json()["code"] == "lot_ended"
    assert db_snapshot(seeded) == before


def test_now_equal_to_ends_at_is_ended_and_one_microsecond_before_is_not(
    monkeypatch: pytest.MonkeyPatch, seeded: sessionmaker[Session]
) -> None:
    lot_id = live_lot(seeded)
    ends_at = lot_state(seeded, lot_id)["ends_at"]

    monkeypatch.setattr(lot_cancellation, "database_now", lambda session: ends_at)
    assert run_cancel(seeded, lot_id) is CancellationRefusal.LOT_ENDED
    assert lot_state(seeded, lot_id)["cancelled_at"] is None

    just_before = ends_at - timedelta(microseconds=1)
    monkeypatch.setattr(lot_cancellation, "database_now", lambda session: just_before)
    result = run_cancel(seeded, lot_id)
    assert isinstance(result, CancelledLot) and result.cancelled_at == just_before


# --- idempotência (I10 a I12) ---


def test_re_cancelling_returns_the_original_timestamp_with_zero_writes(
    auctioneer: TestClient, seeded: sessionmaker[Session], db_engine: Engine
) -> None:
    lot_id = live_lot(seeded)
    first = cancel(auctioneer, lot_id)
    assert first.status_code == 200
    stored = lot_state(seeded, lot_id)["cancelled_at"]
    before = db_snapshot(seeded)

    with statement_recorder(db_engine) as recorder:
        second = cancel(auctioneer, lot_id)

    assert second.status_code == 200
    assert second.json() == first.json()  # a mesma resposta, o mesmo instante
    assert parse(second.json()["cancelled_at"]) == stored
    assert db_snapshot(seeded) == before
    for statement in recorder.statements:
        verb = statement.lstrip().upper()
        assert not verb.startswith(("UPDATE", "INSERT", "DELETE")), statement


def test_re_cancelling_after_the_end_is_still_the_original_200(
    auctioneer: TestClient, seeded: sessionmaker[Session]
) -> None:
    lot_id = live_lot(seeded)
    first = cancel(auctioneer, lot_id)
    now = db_now(seeded)
    tamper(
        seeded,
        "UPDATE lots SET starts_at = :s, ends_at = :e WHERE id = :id",
        s=now - timedelta(hours=3),
        e=now - timedelta(hours=1),
        id=lot_id,
    )

    again = cancel(auctioneer, lot_id)

    assert again.status_code == 200 and again.json() == first.json()


# --- o gate vem antes de tudo (I08, I09, I12) ---

TAMPERINGS = {
    "operational-amount": (
        "UPDATE lots SET current_bid_cents=current_bid_cents+1 WHERE id=:id",
        {},
    ),
    "operational-leader": (
        "UPDATE lots SET current_leader_id=auctioneer_id WHERE id=:id",
        {},
    ),
    "anchor-swapped": (
        "UPDATE lots SET anchor_hmac = :other WHERE id = :id",
        {"other": "b" * 64},
    ),
    "summary-zeroed-old-anchor": (
        "UPDATE lots SET bid_count = 0, current_bid_cents = NULL, "
        "current_leader_id = NULL, final_hash = :genesis WHERE id = :id",
        {"genesis": GENESIS_HASH},
    ),
    "bid-amount-changed": (
        "UPDATE bids SET amount_cents = amount_cents + 1 WHERE lot_id = :id",
        {},
    ),
}


def tamper_with_history(
    factory: sessionmaker[Session], lot_id: uuid.UUID, name: str
) -> None:
    sql, params = TAMPERINGS[name]
    tamper(factory, sql, id=lot_id, **params)


@pytest.mark.parametrize("name", list(TAMPERINGS))
def test_tampered_history_is_409_and_never_decided_by_the_raw_count(
    auctioneer: TestClient, seeded: sessionmaker[Session], name: str
) -> None:
    # O `bid_count` cru de `summary-zeroed-*` diz "sem lances": sem o gate, cancelaria.
    lot_id = lot_with_bid(seeded)
    tamper_with_history(seeded, lot_id, name)
    before = db_snapshot(seeded)

    response = cancel(auctioneer, lot_id)

    assert_integrity_conflict(response)
    assert db_snapshot(seeded) == before  # não cancelou, não reassinou, não reparou


def test_zeroed_summary_with_a_freshly_signed_empty_anchor_is_still_409(
    auctioneer: TestClient, seeded: sessionmaker[Session]
) -> None:
    lot_id = lot_with_bid(seeded)
    tamper(
        seeded,
        "UPDATE lots SET bid_count = 0, current_bid_cents = NULL, "
        "current_leader_id = NULL, final_hash = :g, anchor_hmac = :a WHERE id = :id",
        g=GENESIS_HASH,
        a=empty_anchor(lot_id),
        id=lot_id,
    )
    before = db_snapshot(seeded)

    assert_integrity_conflict(cancel(auctioneer, lot_id))
    assert db_snapshot(seeded) == before


def test_a_legacy_lot_without_an_anchor_is_409_with_no_repair(
    auctioneer: TestClient, seeded: sessionmaker[Session]
) -> None:
    lot_id = insert_lot(seeded, anchored=False, auctioneer_id=DEMO_AUCTIONEER_ID)
    before = db_snapshot(seeded)

    assert_integrity_conflict(cancel(auctioneer, lot_id))
    assert db_snapshot(seeded) == before
    assert lot_state(seeded, lot_id)["anchor_hmac"] is None


@pytest.mark.parametrize("name", ["anchor-swapped", "legacy-null-anchor"])
def test_a_cancelled_and_tampered_lot_is_409_not_the_idempotent_200(
    auctioneer: TestClient, seeded: sessionmaker[Session], name: str
) -> None:
    lot_id = live_lot(seeded)
    assert cancel(auctioneer, lot_id).status_code == 200
    if name == "anchor-swapped":
        tamper(
            seeded,
            "UPDATE lots SET anchor_hmac = :h WHERE id = :id",
            h="c" * 64,
            id=lot_id,
        )
    else:
        tamper(seeded, "UPDATE lots SET anchor_hmac = NULL WHERE id = :id", id=lot_id)
    before = db_snapshot(seeded)

    assert_integrity_conflict(cancel(auctioneer, lot_id))
    assert db_snapshot(seeded) == before


def test_the_gate_runs_before_the_already_cancelled_shortcut(
    monkeypatch: pytest.MonkeyPatch,
    auctioneer: TestClient,
    seeded: sessionmaker[Session],
) -> None:
    lot_id = live_lot(seeded)
    assert cancel(auctioneer, lot_id).status_code == 200
    gate_calls: list[Any] = []
    real = lot_cancellation.authenticate_previous_state
    monkeypatch.setattr(
        lot_cancellation,
        "authenticate_previous_state",
        lambda *a, **k: gate_calls.append(1) or real(*a, **k),
    )

    assert cancel(auctioneer, lot_id).status_code == 200
    assert gate_calls == [1]


@pytest.mark.parametrize("case", ["other-owner", "tampered", "ended"])
def test_every_refusal_releases_the_lot_lock(
    monkeypatch: pytest.MonkeyPatch,
    auctioneer: TestClient,
    seeded: sessionmaker[Session],
    case: str,
) -> None:
    if case == "other-owner":
        add_other_auctioneer(seeded)
        client = client_as(monkeypatch, seeded, OTHER_AUCTIONEER_EMAIL)
        lot_id = live_lot(seeded)
    else:
        client = auctioneer
        if case == "tampered":
            lot_id = live_lot(seeded)
            tamper(
                seeded, "UPDATE lots SET anchor_hmac = NULL WHERE id = :id", id=lot_id
            )
        elif case == "has-bids":
            lot_id = lot_with_bid(seeded)
        else:
            lot_id = ended_lot(seeded)
    assert cancel(client, lot_id).status_code in (403, 409, 422)

    with seeded() as session:  # NOWAIT falha se a trava ainda estiver presa
        locked = session.execute(
            text("SELECT id FROM lots WHERE id = :id FOR UPDATE NOWAIT"), {"id": lot_id}
        ).scalar_one()
        session.rollback()
    assert locked == lot_id


# --- persistência (I09 da story: falha antes do commit) ---


def test_a_failure_after_the_update_and_before_the_commit_leaves_it_uncancelled(
    monkeypatch: pytest.MonkeyPatch, seeded: sessionmaker[Session]
) -> None:
    lot_id = live_lot(seeded)
    client = client_as(
        monkeypatch, seeded, AUCTIONEER_EMAIL, raise_server_exceptions=False
    )

    def boom(self: Session) -> None:
        raise RuntimeError("falha injetada antes do commit")

    with monkeypatch.context() as patch:
        patch.setattr(Session, "commit", boom)
        response = cancel(client, lot_id)

    assert response.status_code == 500
    assert response.json()["code"] == "internal_error"
    assert lot_state(seeded, lot_id)["cancelled_at"] is None  # sem estado parcial


# --- leituras públicas e do dono (I15, I16) ---


def test_a_cancelled_lot_disappears_from_every_public_read(
    auctioneer: TestClient,
    anonymous: TestClient,
    bidder: TestClient,
    seeded: sessionmaker[Session],
    db_engine: Engine,
) -> None:
    lot_id = live_lot(seeded)
    assert cancel(auctioneer, lot_id).status_code == 200
    before = db_snapshot(seeded)

    with statement_recorder(db_engine) as recorder:
        showcase = anonymous.get("/api/lots")
        detail = anonymous.get(f"/api/lots/{lot_id}")
        room = anonymous.get(f"/api/lots/{lot_id}/bids")
        mine = bidder.get(f"/api/lots/{lot_id}/bids/mine")

    body = showcase.json()
    assert showcase.status_code == 200
    # Só há lote cancelado: o `as_of` e as três listas continuam presentes.
    assert sorted(body) == ["as_of", "ended", "live", "scheduled"]
    assert body["live"] == body["scheduled"] == body["ended"] == []
    assert body["as_of"].endswith("Z")
    for response in (detail, room, mine):
        assert (response.status_code, response.json()["code"]) == (404, "not_found")
    assert db_snapshot(seeded) == before  # nenhuma leitura escreve (AD-19)
    for statement in recorder.statements:
        verb = statement.lstrip().upper()
        assert not verb.startswith(("UPDATE", "INSERT", "DELETE")), statement


def test_other_lots_stay_public_and_no_phase_is_cancelled(
    auctioneer: TestClient, anonymous: TestClient, seeded: sessionmaker[Session]
) -> None:
    kept = live_lot(seeded)
    gone = live_lot(seeded)
    assert cancel(auctioneer, gone).status_code == 200

    body = anonymous.get("/api/lots").json()
    detail = anonymous.get(f"/api/lots/{kept}")

    assert [item["id"] for item in body["live"]] == [str(kept)]
    assert detail.status_code == 200 and detail.json()["lot"]["phase"] == "live"
    assert len(detail.json()["lot"]) == 19  # inclui current_bid_cents
    assert detail.json()["lot"]["current_bid_cents"] is None
    assert detail.json()["lot"]["settlement_status"] == "pending"


def test_the_owner_still_lists_the_cancelled_lot_with_the_new_fields(
    auctioneer: TestClient, seeded: sessionmaker[Session]
) -> None:
    cancelled = live_lot(seeded)
    open_lot = live_lot(seeded)
    with_bid = lot_with_bid(seeded)
    assert cancel(auctioneer, cancelled).status_code == 200
    stored = lot_state(seeded, cancelled)["cancelled_at"]

    response = auctioneer.get("/api/lots/mine")

    body = response.json()
    assert response.status_code == 200 and sorted(body) == [
        "as_of",
        "items",
        "total_received_cents",
    ]
    by_id = {item["id"]: item for item in body["items"]}
    assert set(by_id) == {str(cancelled), str(open_lot), str(with_bid)}
    assert parse(by_id[str(cancelled)]["cancelled_at"]) == stored
    assert by_id[str(open_lot)]["cancelled_at"] is None
    assert by_id[str(open_lot)]["bid_count"] == 0
    assert by_id[str(with_bid)]["bid_count"] == 1
    for item in by_id.values():
        assert item["phase"] == "live" and len(item) == 23
        assert item["settlement_status"] == "pending" and item["settlement"] is None


def test_a_cancelled_lot_that_later_ended_keeps_its_temporal_phase_for_the_owner(
    auctioneer: TestClient, seeded: sessionmaker[Session]
) -> None:
    lot_id = live_lot(seeded)
    assert cancel(auctioneer, lot_id).status_code == 200
    now = db_now(seeded)
    tamper(
        seeded,
        "UPDATE lots SET starts_at = :s, ends_at = :e WHERE id = :id",
        s=now - timedelta(hours=3),
        e=now - timedelta(hours=1),
        id=lot_id,
    )

    (item,) = auctioneer.get("/api/lots/mine").json()["items"]

    assert item["phase"] == "ended" and item["cancelled_at"] is not None


def test_the_owner_list_with_only_cancelled_or_no_lots_still_has_as_of(
    auctioneer: TestClient, seeded: sessionmaker[Session]
) -> None:
    assert auctioneer.get("/api/lots/mine").json()["items"] == []
    lot_id = live_lot(seeded)
    assert cancel(auctioneer, lot_id).status_code == 200

    body = auctioneer.get("/api/lots/mine").json()

    assert body["as_of"].endswith("Z") and len(body["items"]) == 1


# --- lance em lote cancelado (I18, D4) ---


def post_bid(client: TestClient, lot_id: uuid.UUID, amount: int = 10_000) -> Any:
    return client.post(
        f"/api/lots/{lot_id}/bids",
        json={"amount_cents": amount},
        headers=json_headers(HTTPS_ORIGIN),
    )


@pytest.mark.parametrize("scheduled", [False, True], ids=["live", "scheduled"])
def test_a_bid_on_a_cancelled_lot_is_422_lot_cancelled_with_zero_effects(
    auctioneer: TestClient,
    bidder: TestClient,
    seeded: sessionmaker[Session],
    db_engine: Engine,
    scheduled: bool,
) -> None:
    lot_id = scheduled_lot(seeded) if scheduled else live_lot(seeded)
    assert cancel(auctioneer, lot_id).status_code == 200
    before = db_snapshot(seeded)

    with statement_log(db_engine) as log:
        response = post_bid(bidder, lot_id)

    assert response.status_code == 422
    assert response.json() == {
        "status": 422,
        "code": "lot_cancelled",
        "message": "Este lote foi cancelado.",
    }
    assert db_snapshot(seeded) == before  # nenhum lance, nenhuma carteira
    assert locked_wallet_ids(log) == []
    assert_invariants(seeded)


def test_the_gate_precedes_lot_cancelled_in_the_bid_path(
    auctioneer: TestClient, bidder: TestClient, seeded: sessionmaker[Session]
) -> None:
    tampered = live_lot(seeded)
    legacy = live_lot(seeded)
    for lot_id in (tampered, legacy):
        assert cancel(auctioneer, lot_id).status_code == 200
    tamper(
        seeded,
        "UPDATE lots SET anchor_hmac = :h WHERE id = :id",
        h="d" * 64,
        id=tampered,
    )
    tamper(seeded, "UPDATE lots SET anchor_hmac = NULL WHERE id = :id", id=legacy)
    before = db_snapshot(seeded)

    assert_integrity_conflict(post_bid(bidder, tampered))
    assert_integrity_conflict(post_bid(bidder, legacy))
    assert db_snapshot(seeded) == before


def test_a_cancelled_lot_that_ended_is_still_lot_cancelled_for_a_bid(
    auctioneer: TestClient, bidder: TestClient, seeded: sessionmaker[Session]
) -> None:
    lot_id = live_lot(seeded)
    assert cancel(auctioneer, lot_id).status_code == 200
    now = db_now(seeded)
    tamper(
        seeded,
        "UPDATE lots SET starts_at = :s, ends_at = :e WHERE id = :id",
        s=now - timedelta(hours=3),
        e=now - timedelta(hours=1),
        id=lot_id,
    )

    assert post_bid(bidder, lot_id).json()["code"] == "lot_cancelled"


def test_cancelled_at_is_never_written_by_the_bid_path(
    bidder: TestClient, seeded: sessionmaker[Session]
) -> None:
    lot_id = live_lot(seeded)
    assert post_bid(bidder, lot_id).status_code == 201
    assert lot_state(seeded, lot_id)["cancelled_at"] is None
    assert integrity()  # segredos de teste vêm de `integrity()`, nunca de `.env*`


@pytest.mark.parametrize(
    "case", ["insufficient", "missing", "negative", "above-total", "above-limit"]
)
def test_inconsistent_wallet_returns_generic_500_without_partial_cancellation(
    monkeypatch, seeded, case
):
    from app.money import MAX_CENTS
    from tests.wallet_support import delete_wallet

    lot_id = lot_with_bid(seeded)
    if case == "insufficient":
        set_wallet(seeded, ALICE, 1_000_000, 9_999)
    elif case == "missing":
        delete_wallet(seeded, ALICE)
    else:
        original_lock = lot_cancellation.lock_wallet

        def corrupt(session, user_id):
            wallet = original_lock(session, user_id)
            if case == "negative":
                wallet.committed_balance_cents = -1
            elif case == "above-total":
                wallet.committed_balance_cents = wallet.total_balance_cents + 1
            else:
                wallet.total_balance_cents = MAX_CENTS + 1
            return wallet

        monkeypatch.setattr(lot_cancellation, "lock_wallet", corrupt)
    before = db_snapshot(seeded)
    client = client_as(
        monkeypatch, seeded, AUCTIONEER_EMAIL, raise_server_exceptions=False
    )
    response = cancel(client, lot_id)
    assert response.status_code == 500
    assert response.json() == {
        "status": 500,
        "code": "internal_error",
        "message": "Erro interno. Tente novamente mais tarde.",
    }
    assert db_snapshot(seeded) == before


@pytest.mark.parametrize("stage", ["wallet-update", "lot-update", "precommit"])
def test_failure_during_refund_rolls_back_wallet_lot_and_history(
    monkeypatch, seeded, db_engine, stage
):
    from sqlalchemy import event

    lot_id = lot_with_bid(seeded)
    before = db_snapshot(seeded)
    client = client_as(
        monkeypatch, seeded, AUCTIONEER_EMAIL, raise_server_exceptions=False
    )
    hits = []

    def fail_after_update(conn, cursor, statement, params, context, many):
        sql = statement.lstrip().upper()
        if (stage == "wallet-update" and sql.startswith("UPDATE WALLETS")) or (
            stage == "lot-update" and sql.startswith("UPDATE LOTS")
        ):
            hits.append(stage)
            raise RuntimeError("injected cancellation failure")

    def fail_commit(session):
        hits.append(stage)
        raise RuntimeError("injected cancellation failure")

    event.listen(db_engine, "after_cursor_execute", fail_after_update)
    try:
        if stage == "precommit":
            monkeypatch.setattr(Session, "commit", fail_commit)
        response = cancel(client, lot_id)
    finally:
        event.remove(db_engine, "after_cursor_execute", fail_after_update)
    assert response.status_code == 500 and response.json()["code"] == "internal_error"
    assert hits == [stage]
    assert db_snapshot(seeded) == before


def test_cancelled_history_still_detects_tampering_before_idempotence(
    auctioneer, anonymous, seeded
):
    lot_id = lot_with_bid(seeded)
    assert cancel(auctioneer, lot_id).status_code == 200
    tamper(
        seeded,
        "UPDATE bids SET amount_cents=amount_cents+1 WHERE lot_id=:id",
        id=lot_id,
    )
    before = db_snapshot(seeded)
    assert_integrity_conflict(cancel(auctioneer, lot_id))
    audit = anonymous.get(f"/api/lots/{lot_id}/audit").json()
    assert audit["integrity"] == "adulterated" and audit["bids"] == []
    assert db_snapshot(seeded) == before


def test_settled_lot_is_never_refunded_and_cancelled_settlement_is_corrupt(
    auctioneer, anonymous, seeded
):
    from tests.settlement_support import expire, run_settle

    lot_id = lot_with_bid(seeded)
    expire(seeded, lot_id)
    assert run_settle(seeded, lot_id).transitioned
    before = db_snapshot(seeded)
    assert cancel(auctioneer, lot_id).json()["code"] == "lot_ended"
    assert db_snapshot(seeded) == before
    tamper(
        seeded,
        "UPDATE lots SET cancelled_at=:now WHERE id=:id",
        now=db_now(seeded),
        id=lot_id,
    )
    before = db_snapshot(seeded)
    assert_integrity_conflict(cancel(auctioneer, lot_id))
    assert (
        anonymous.get(f"/api/lots/{lot_id}/audit").json()["integrity"] == "adulterated"
    )
    assert db_snapshot(seeded) == before


def test_idempotent_refund_does_not_revisit_missing_wallet(
    auctioneer, seeded, db_engine
):
    from tests.wallet_support import delete_wallet

    lot_id = lot_with_bid(seeded)
    first = cancel(auctioneer, lot_id)
    assert first.status_code == 200
    delete_wallet(seeded, ALICE)
    before = db_snapshot(seeded)
    with statement_log(db_engine) as log:
        second = cancel(auctioneer, lot_id)
    assert second.status_code == 200 and second.json() == first.json()
    assert not log.saw("wallets")
    assert db_snapshot(seeded) == before
