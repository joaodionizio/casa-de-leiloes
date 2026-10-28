"""`GET /api/lots/{lot_id}/bids` e `/bids/mine` sobre PostgreSQL real (Story 3.5;
CAP-1, CAP-2, CAP-5). Só as leituras: concorrência, travas, rollback e hash/HMAC são da
3.4. Dinheiro sempre como inteiro, nunca `float`."""

import re
import uuid
from datetime import timedelta

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

from app import bids
from app.bid_integrity import generate_bidder_alias
from app.errors import MESSAGES
from app.money import MAX_CENTS
from tests.auth_support import (
    AUCTIONEER_EMAIL,
    BIDDER_EMAIL,
    HTTPS_ORIGIN,
    OTHER_BIDDER_EMAIL,
    build_client,
    cookie_name_of,
    json_headers,
    login,
    seeded_id,
)
from tests.bid_support import (
    add_bidder,
    db_snapshot,
    integrity,
    live_lot,
    lot_state,
    run_bid,
)
from tests.lot_support import db_now, integrity_secrets, normalized, statement_recorder
from tests.wallet_support import seed_users_with_wallets, set_wallet

ALICE = seeded_id(BIDDER_EMAIL)
BOB = seeded_id(OTHER_BIDDER_EMAIL)
ROOM_KEYS = [
    "as_of",
    "bid_count",
    "bids",
    "current_bid_cents",
    "ends_at",
    "minimum_next_bid_cents",
    "phase",
    "settlement",
    "settlement_status",
]
BID_KEYS = ["amount_cents", "bidder_alias", "placed_at", "sequence"]
MINE_KEYS = ["bidder_alias", "last_bid_cents", "my_bid_count"]
ALIAS = re.compile(r"^Licitante-[0-9A-F]{16}$")
FORBIDDEN_NAMES = (
    "bidder_id",
    "user_id",
    "current_leader_id",
    "auctioneer_id",
    "email",
    "previous_hash",
    "current_hash",
    "final_hash",
    "anchor_hmac",
    "canonical_version",
)


@pytest.fixture
def seeded(
    db_session_factory: sessionmaker[Session], clean_users: None
) -> sessionmaker[Session]:
    seed_users_with_wallets(db_session_factory)
    set_wallet(db_session_factory, ALICE, 10_000_000)
    set_wallet(db_session_factory, BOB, 10_000_000)
    return db_session_factory


def client_for(
    monkeypatch: pytest.MonkeyPatch,
    seeded: sessionmaker[Session],
    email: str | None = BIDDER_EMAIL,
) -> TestClient:
    client = build_client(monkeypatch, HTTPS_ORIGIN, session_factory=seeded)
    if email is not None:
        assert login(client, HTTPS_ORIGIN, email).status_code == 200
    return client


def room(lot_id: object) -> str:
    return f"/api/lots/{lot_id}/bids"


def mine(lot_id: object) -> str:
    return f"/api/lots/{lot_id}/bids/mine"


def alias_of(lot_id: uuid.UUID, user_id: uuid.UUID) -> str:
    return generate_bidder_alias(
        lot_id=lot_id, user_id=user_id, pseudonym_secret=integrity_secrets()[1]
    )


def place_many(seeded: sessionmaker[Session], lot_id: uuid.UUID, count: int) -> None:
    """`count` lances pelo serviço real, Alice nos ímpares e Bob nos pares."""
    for number in range(1, count + 1):
        who = ALICE if number % 2 else BOB
        placed = run_bid(seeded, lot_id, who, 10_000 + number * 1_000 - 1_000)
        assert not isinstance(placed, str), placed
        assert hasattr(placed, "sequence"), placed


def error_of(response, status: int, code: str) -> None:  # type: ignore[no-untyped-def]
    assert response.status_code == status
    assert response.headers["cache-control"] == "no-store"
    assert response.json() == {
        "status": status,
        "code": code,
        "message": MESSAGES[code],
    }


# --- B1, B2: contrato exato e lote sem lances ---


def test_an_empty_lot_reads_with_the_exact_public_contract(
    monkeypatch: pytest.MonkeyPatch, seeded: sessionmaker[Session]
) -> None:
    lot_id = live_lot(seeded, starting_bid_cents=12_500, min_increment_cents=500)
    anonymous = client_for(monkeypatch, seeded, None)

    response = anonymous.get(room(lot_id))

    assert response.status_code == 200
    assert response.headers["cache-control"] == "no-store"
    body = response.json()
    assert sorted(body) == ROOM_KEYS
    assert body["phase"] == "live"
    assert body["current_bid_cents"] is None
    assert body["minimum_next_bid_cents"] == 12_500
    assert body["bid_count"] == 0
    assert body["bids"] == []
    assert body["as_of"].endswith("Z")
    assert body["ends_at"].endswith("Z")


def test_a_lot_without_bids_gives_the_bidder_a_stable_alias_and_no_participation(
    monkeypatch: pytest.MonkeyPatch, seeded: sessionmaker[Session]
) -> None:
    lot_id = live_lot(seeded)
    alice = client_for(monkeypatch, seeded)

    first = alice.get(mine(lot_id))
    second = alice.get(mine(lot_id))

    assert first.status_code == 200
    assert first.headers["cache-control"] == "no-store"
    body = first.json()
    assert sorted(body) == MINE_KEYS
    assert ALIAS.match(body["bidder_alias"])
    assert body["bidder_alias"] == alias_of(lot_id, ALICE)
    assert body["my_bid_count"] == 0
    assert body["last_bid_cents"] is None
    assert second.json() == body


# --- B3: a janela de 50 ---


def test_fifty_one_bids_return_the_fifty_latest_in_descending_sequence(
    monkeypatch: pytest.MonkeyPatch, seeded: sessionmaker[Session]
) -> None:
    lot_id = live_lot(seeded, ends_at=db_now(seeded) + timedelta(days=1))
    place_many(seeded, lot_id, 51)
    # O desempate é a sequência, nunca o instante: empata todos os `placed_at`.
    with seeded() as session:
        session.execute(
            text("UPDATE bids SET placed_at = :at WHERE lot_id = :id"),
            {"at": db_now(seeded), "id": lot_id},
        )
        session.commit()
    anonymous = client_for(monkeypatch, seeded, None)

    body = anonymous.get(room(lot_id)).json()

    assert body["bid_count"] == 51
    assert [item["sequence"] for item in body["bids"]] == list(range(51, 1, -1))
    assert all(sorted(item) == BID_KEYS for item in body["bids"])
    first = body["bids"][0]
    assert first["sequence"] == body["bid_count"]
    assert first["amount_cents"] == body["current_bid_cents"] == 10_000 + 50 * 1_000
    assert body["minimum_next_bid_cents"] == body["current_bid_cents"] + 1_000


# --- B4: a participação própria fora da janela ---


def test_my_bids_count_all_of_my_bids_even_outside_the_public_window(
    monkeypatch: pytest.MonkeyPatch, seeded: sessionmaker[Session]
) -> None:
    lot_id = live_lot(seeded, ends_at=db_now(seeded) + timedelta(days=1))
    # Alice dá só o lance 1; Bob (pares) e Carol (ímpares) dão os outros 50.
    carol = add_bidder(seeded, 10_000_000)
    assert hasattr(run_bid(seeded, lot_id, ALICE, 10_000), "sequence")
    for number in range(2, 52):
        who = BOB if number % 2 == 0 else carol
        assert hasattr(
            run_bid(seeded, lot_id, who, 10_000 + (number - 1) * 1_000), "sequence"
        )
    alice = client_for(monkeypatch, seeded)
    bob = client_for(monkeypatch, seeded, OTHER_BIDDER_EMAIL)

    public = alice.get(room(lot_id)).json()
    alice_mine = alice.get(mine(lot_id)).json()
    bob_mine = bob.get(mine(lot_id)).json()

    assert public["bid_count"] == 51
    assert alice_mine["bidder_alias"] not in {i["bidder_alias"] for i in public["bids"]}
    assert alice_mine["my_bid_count"] == 1
    assert alice_mine["last_bid_cents"] == 10_000
    assert bob_mine["my_bid_count"] == 25
    assert bob_mine["last_bid_cents"] == 10_000 + 49 * 1_000  # sequência 50


def test_my_last_bid_is_the_one_with_the_highest_sequence(
    monkeypatch: pytest.MonkeyPatch, seeded: sessionmaker[Session]
) -> None:
    lot_id = live_lot(seeded)
    place_many(seeded, lot_id, 5)
    alice = client_for(monkeypatch, seeded)

    body = alice.get(mine(lot_id)).json()

    assert body["my_bid_count"] == 3  # sequências 1, 3 e 5
    assert body["last_bid_cents"] == 14_000


# --- B5: mínimo e fases ---


def test_the_minimum_is_the_domain_result_including_the_representable_limit(
    monkeypatch: pytest.MonkeyPatch, seeded: sessionmaker[Session]
) -> None:
    anonymous = client_for(monkeypatch, seeded, None)
    exact = live_lot(
        seeded,
        starting_bid_cents=MAX_CENTS - 1_000,
        min_increment_cents=1_000,
    )
    over = live_lot(
        seeded,
        starting_bid_cents=MAX_CENTS - 999,
        min_increment_cents=1_000,
    )
    at_max = live_lot(seeded, starting_bid_cents=MAX_CENTS, min_increment_cents=1)
    # Uma carteira por lance: cada um compromete quase o teto inteiro.
    for lot_id, amount in (
        (exact, MAX_CENTS - 1_000),
        (over, MAX_CENTS - 999),
        (at_max, MAX_CENTS),
    ):
        bidder = add_bidder(seeded, MAX_CENTS)
        assert hasattr(run_bid(seeded, lot_id, bidder, amount), "sequence")

    assert anonymous.get(room(exact)).json()["minimum_next_bid_cents"] == MAX_CENTS
    assert anonymous.get(room(over)).json()["minimum_next_bid_cents"] is None
    assert anonymous.get(room(at_max)).json()["minimum_next_bid_cents"] is None


def test_scheduled_and_ended_lots_keep_the_same_contract(
    monkeypatch: pytest.MonkeyPatch, seeded: sessionmaker[Session]
) -> None:
    now = db_now(seeded)
    scheduled = live_lot(
        seeded,
        starts_at=now + timedelta(hours=1),
        ends_at=now + timedelta(hours=2),
        starting_bid_cents=20_000,
    )
    ended = live_lot(
        seeded,
        starts_at=now - timedelta(hours=3),
        ends_at=now - timedelta(hours=2),
        starting_bid_cents=30_000,
    )
    anonymous = client_for(monkeypatch, seeded, None)

    future = anonymous.get(room(scheduled)).json()
    past = anonymous.get(room(ended)).json()

    assert (future["phase"], future["minimum_next_bid_cents"]) == ("scheduled", 20_000)
    assert (past["phase"], past["minimum_next_bid_cents"]) == ("ended", 30_000)
    assert sorted(future) == sorted(past) == ROOM_KEYS


# --- B6, B7: políticas, 404/422 e headers ---


def test_the_public_room_is_equal_for_every_caller_and_never_reads_users(
    monkeypatch: pytest.MonkeyPatch,
    seeded: sessionmaker[Session],
    db_engine: Engine,
) -> None:
    lot_id = live_lot(seeded)
    place_many(seeded, lot_id, 2)
    callers = [
        client_for(monkeypatch, seeded, None),
        client_for(monkeypatch, seeded),
        client_for(monkeypatch, seeded, AUCTIONEER_EMAIL),
    ]
    invalid = client_for(monkeypatch, seeded, None)
    invalid.cookies.set(cookie_name_of(invalid), "not-a-token")

    bodies = []
    for caller in (*callers, invalid):
        with statement_recorder(db_engine) as recorder:
            response = caller.get(room(lot_id))
        assert response.status_code == 200
        assert not any("users" in s.lower() for s in recorder.statements)
        body = response.json()
        body.pop("as_of")
        bodies.append(body)

    assert all(body == bodies[0] for body in bodies)


def test_mine_requires_a_bidder_and_an_existing_lot(
    monkeypatch: pytest.MonkeyPatch, seeded: sessionmaker[Session]
) -> None:
    lot_id = live_lot(seeded)

    error_of(
        client_for(monkeypatch, seeded, None).get(mine(lot_id)), 401, "unauthorized"
    )
    error_of(
        client_for(monkeypatch, seeded, AUCTIONEER_EMAIL).get(mine(lot_id)),
        403,
        "forbidden",
    )
    error_of(client_for(monkeypatch, seeded).get(mine(uuid.uuid4())), 404, "not_found")


def test_an_unknown_lot_is_a_404_and_a_malformed_id_is_a_422(
    monkeypatch: pytest.MonkeyPatch, seeded: sessionmaker[Session]
) -> None:
    anonymous = client_for(monkeypatch, seeded, None)
    alice = client_for(monkeypatch, seeded)

    error_of(anonymous.get(room(uuid.uuid4())), 404, "not_found")
    for response in (anonymous.get(room("nope")), alice.get(mine("nope"))):
        assert response.status_code == 422
        assert response.json()["code"] == "validation_error"


# --- B8: uma instrução, sem trava, sem escrita ---


def test_the_public_room_runs_one_read_only_statement_with_one_clock(
    monkeypatch: pytest.MonkeyPatch,
    seeded: sessionmaker[Session],
    db_engine: Engine,
) -> None:
    lot_id = live_lot(seeded)
    anonymous = client_for(monkeypatch, seeded, None)

    with statement_recorder(db_engine) as recorder:
        assert anonymous.get(room(lot_id)).status_code == 200

    assert len(recorder.statements) == 1
    statement = normalized(recorder.statements[0])
    upper = statement.upper()
    assert statement.count("clock_timestamp()") == 1
    assert statement.startswith("WITH clock AS MATERIALIZED")
    assert "LATERAL" in upper and "LIMIT" in upper and "DESC" in upper
    for forbidden in (
        "FOR UPDATE",
        "FOR SHARE",
        "INSERT",
        "UPDATE ",
        "DELETE",
        "BIDDER_ID",
        "PREVIOUS_HASH",
        "CURRENT_HASH",
        "ANCHOR_HMAC",
    ):
        assert forbidden not in upper


def test_mine_runs_one_business_statement_after_the_authentication_select(
    monkeypatch: pytest.MonkeyPatch,
    seeded: sessionmaker[Session],
    db_engine: Engine,
) -> None:
    lot_id = live_lot(seeded)
    alice = client_for(monkeypatch, seeded)

    with statement_recorder(db_engine) as recorder:
        assert alice.get(mine(lot_id)).status_code == 200

    statements = [normalized(s).upper() for s in recorder.statements]
    assert len(statements) == 2
    assert "FROM USERS" in statements[0]
    business = statements[1]
    assert "COUNT(" in business and "LIMIT" in business
    for forbidden in ("FOR UPDATE", "INSERT", "UPDATE ", "DELETE", "HASH", "HMAC"):
        assert forbidden not in business


# --- B9: nada é escrito, alias só do próprio ---


def test_reads_leave_the_persisted_state_untouched_in_every_phase_and_for_legacy_lots(
    monkeypatch: pytest.MonkeyPatch, seeded: sessionmaker[Session]
) -> None:
    now = db_now(seeded)
    live = live_lot(seeded, ends_at=now + timedelta(days=1))
    place_many(seeded, live, 3)
    ended = live_lot(
        seeded, starts_at=now - timedelta(hours=3), ends_at=now - timedelta(hours=2)
    )
    legacy = live_lot(seeded, anchored=False)
    before = db_snapshot(seeded)
    alice = client_for(monkeypatch, seeded)

    for lot_id in (live, ended, legacy):
        assert alice.get(room(lot_id)).status_code == 200
        assert alice.get(mine(lot_id)).status_code == 200

    assert db_snapshot(seeded) == before
    assert lot_state(seeded, legacy)["anchor_hmac"] is None


def test_the_alias_generator_runs_only_for_the_session_user_on_mine(
    monkeypatch: pytest.MonkeyPatch, seeded: sessionmaker[Session]
) -> None:
    lot_id = live_lot(seeded)
    place_many(seeded, lot_id, 2)
    calls: list[uuid.UUID] = []
    real = bids.generate_bidder_alias

    def spy(**kwargs):  # type: ignore[no-untyped-def]
        calls.append(kwargs["user_id"])
        return real(**kwargs)

    monkeypatch.setattr(bids, "generate_bidder_alias", spy)
    anonymous = client_for(monkeypatch, seeded, None)
    alice = client_for(monkeypatch, seeded)

    assert anonymous.get(room(lot_id)).status_code == 200
    assert calls == []
    assert alice.get(mine(lot_id)).status_code == 200
    assert calls == [ALICE]


# --- B10: reflexo do 201 ---


def test_a_real_bid_with_anti_sniping_is_reflected_by_the_next_read(
    monkeypatch: pytest.MonkeyPatch, seeded: sessionmaker[Session]
) -> None:
    now = db_now(seeded)
    lot_id = live_lot(seeded, ends_at=now + timedelta(seconds=90))
    alice = client_for(monkeypatch, seeded)

    posted = alice.post(
        room(lot_id), json={"amount_cents": 10_000}, headers=json_headers(HTTPS_ORIGIN)
    )
    body = alice.get(room(lot_id)).json()
    private = alice.get(mine(lot_id)).json()

    assert posted.status_code == 201
    assert posted.json()["lot"]["anti_sniping_applied"] is True
    assert body["ends_at"] == posted.json()["lot"]["ends_at"]
    assert body["bids"] == [posted.json()["bid"]]
    assert body["current_bid_cents"] == 10_000
    assert private["bidder_alias"] == posted.json()["bid"]["bidder_alias"]
    assert (private["my_bid_count"], private["last_bid_cents"]) == (1, 10_000)


# --- B11: privacidade de chaves e valores ---


def walk(value: object) -> list[str]:
    if isinstance(value, dict):
        return [k for k in value] + [s for v in value.values() for s in walk(v)]
    if isinstance(value, list):
        return [s for v in value for s in walk(v)]
    return [str(value)]


def test_responses_never_carry_private_keys_or_values(
    monkeypatch: pytest.MonkeyPatch, seeded: sessionmaker[Session]
) -> None:
    lot_id = live_lot(seeded)
    place_many(seeded, lot_id, 3)
    state = lot_state(seeded, lot_id)
    alice = client_for(monkeypatch, seeded)
    audit, pseudonym = integrity_secrets()
    private_values = {
        str(ALICE),
        str(BOB),
        BIDDER_EMAIL,
        OTHER_BIDDER_EMAIL,
        AUCTIONEER_EMAIL,
        state["final_hash"],
        state["anchor_hmac"],
        audit.decode(),
        pseudonym.decode(),
        str(integrity().audit_hmac_secret),
    }

    for response in (alice.get(room(lot_id)), alice.get(mine(lot_id))):
        text_body = response.text
        found = walk(response.json())
        assert not any(name in found for name in FORBIDDEN_NAMES)
        assert not any(value in text_body for value in private_values)
    for row in alice.get(room(lot_id)).json()["bids"]:
        assert ALIAS.match(row["bidder_alias"])
