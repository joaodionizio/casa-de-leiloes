"""O gate de integridade sobre PostgreSQL real (Story 3.4; T-GATE G1 a G23, G9b, G10b,
G11b; CAP-2, CA7).

Um lote com três lances legítimos é adulterado direto no banco e um lance legítimo é
tentado: a resposta é sempre o mesmo 409, o banco não muda, nenhuma carteira é travada e
nenhuma HMAC nova é gravada. As CHECKs só são removidas pela fixture `drop_checks`, que
recria exatamente o que removeu."""

import logging
import uuid
from collections.abc import Callable
from dataclasses import dataclass
from datetime import timedelta
from typing import Any

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

from app.bid_integrity import (
    GENESIS_HASH,
    AnchorState,
    CanonicalBid,
    compute_anchor_hmac,
    compute_bid_hash,
    generate_bidder_alias,
)
from app.bids import IntegrityConflict, IntegrityFailure, PlacedBid
from tests.auth_support import (
    BIDDER_EMAIL,
    HTTPS_ORIGIN,
    OTHER_BIDDER_EMAIL,
    build_client,
    json_headers,
    login,
    seeded_id,
)
from tests.bid_support import (
    bid_rows,
    db_snapshot,
    drop_checks,  # noqa: F401  (fixture)
    integrity_secrets,
    live_lot,
    lot_state,
    read_checks,
    run_bid,
    service_trace,
    statement_log,
    tamper,
)
from tests.lot_support import db_now
from tests.wallet_support import seed_users_with_wallets, set_wallet

ALICE = seeded_id(BIDDER_EMAIL)
BOB = seeded_id(OTHER_BIDDER_EMAIL)
INTEGRITY_BODY = {
    "status": 409,
    "code": "lot_integrity_conflict",
    "message": "Não foi possível verificar a integridade deste lote. "
    "O lance não foi registrado.",
}
F = IntegrityFailure
OTHER_HASH = "c" * 64


@pytest.fixture
def seeded(
    db_session_factory: sessionmaker[Session], clean_users: None
) -> sessionmaker[Session]:
    seed_users_with_wallets(db_session_factory)
    set_wallet(db_session_factory, ALICE, 1_000_000)
    set_wallet(db_session_factory, BOB, 1_000_000)
    return db_session_factory


@pytest.fixture
def bob_client(
    monkeypatch: pytest.MonkeyPatch, seeded: sessionmaker[Session]
) -> TestClient:
    client = build_client(monkeypatch, HTTPS_ORIGIN, session_factory=seeded)
    client = TestClient(
        client.app, base_url=HTTPS_ORIGIN, raise_server_exceptions=False
    )
    assert login(client, HTTPS_ORIGIN, OTHER_BIDDER_EMAIL).status_code == 200
    return client


@dataclass
class Case:
    factory: sessionmaker[Session]
    lot_id: uuid.UUID
    drop: Callable[..., None]


def chained_lot(factory: sessionmaker[Session], **columns: Any) -> uuid.UUID:
    """Três lances legítimos: Alice 10 000, Bob 11 000, Alice 12 000 (líder: Alice)."""
    lot_id = live_lot(factory, starting_bid_cents=10_000, **columns)
    for user, amount in ((ALICE, 10_000), (BOB, 11_000), (ALICE, 12_000)):
        assert isinstance(run_bid(factory, lot_id, user, amount), PlacedBid)
    return lot_id


def rebuild(
    factory: sessionmaker[Session],
    lot_id: uuid.UUID,
    entries: list[tuple[uuid.UUID, int]],
    *,
    base: list[dict[str, Any]],
) -> str:
    """Apaga o histórico e o regrava como um atacante que recalcula a cadeia inteira:
    `entries` = `(licitante, valor)` na nova ordem; devolve o novo hash final. Os
    horários reaproveitam os de `base` (ou o último)."""
    _, pseudonym = integrity_secrets()
    previous = GENESIS_HASH
    rows: list[dict[str, Any]] = []
    for index, (user, amount) in enumerate(entries):
        moment = base[min(index, len(base) - 1)]["placed_at"]
        alias = generate_bidder_alias(
            lot_id=lot_id, user_id=user, pseudonym_secret=pseudonym
        )
        canonical = CanonicalBid(
            v=1,
            lot_id=lot_id,
            sequence=index + 1,
            bidder_alias=alias,
            amount_cents=amount,
            timestamp=moment,
            previous_hash=previous,
        )
        current = compute_bid_hash(canonical)
        rows.append(
            {
                "lot_id": lot_id,
                "sequence": index + 1,
                "bidder_id": user,
                "bidder_alias": alias,
                "amount_cents": amount,
                "placed_at": moment,
                "previous_hash": previous,
                "current_hash": current,
                "canonical_version": 1,
            }
        )
        previous = current
    with factory() as session:
        session.execute(text("DELETE FROM bids WHERE lot_id = :id"), {"id": lot_id})
        for row in rows:
            session.execute(
                text(
                    "INSERT INTO bids (lot_id, sequence, bidder_id, bidder_alias, "
                    "amount_cents, placed_at, previous_hash, current_hash, "
                    "canonical_version) VALUES (:lot_id, :sequence, :bidder_id, "
                    ":bidder_alias, :amount_cents, :placed_at, :previous_hash, "
                    ":current_hash, :canonical_version)"
                ),
                row,
            )
        session.commit()
    return previous


def set_lot(case: Case, **columns: Any) -> None:
    assignments = ", ".join(f"{name} = :{name}" for name in columns)
    tamper(
        case.factory,
        f"UPDATE lots SET {assignments} WHERE id = :id",  # noqa: S608
        id=case.lot_id,
        **columns,
    )


def original(case: Case) -> list[dict[str, Any]]:
    return bid_rows(case.factory, case.lot_id)


# --- adulterações: o próximo lance legítimo de Bob (13 000) não pode ter efeito ---


def g1(c: Case) -> None:
    tamper(
        c.factory,
        "UPDATE bids SET amount_cents = amount_cents + 1 WHERE lot_id = :id "
        "AND sequence = 1",
        id=c.lot_id,
    )


def g2(c: Case) -> None:  # S-01: cadeia recalculada, resumo novo, HMAC antiga
    base = original(c)
    final = rebuild(
        c.factory,
        c.lot_id,
        [(ALICE, 10_001), (BOB, 11_000), (ALICE, 12_000)],
        base=base,
    )
    set_lot(c, final_hash=final)


def g3(c: Case) -> None:  # cadeia recalculada, resumo e HMAC antigos
    base = original(c)
    rebuild(
        c.factory,
        c.lot_id,
        [(ALICE, 10_001), (BOB, 11_000), (ALICE, 12_000)],
        base=base,
    )


def g4(c: Case) -> None:  # último lance apagado
    tamper(
        c.factory,
        "DELETE FROM bids WHERE lot_id = :id AND sequence = 3",
        id=c.lot_id,
    )


def g5(c: Case) -> None:  # último apagado e resumo ajustado ao anterior
    second = original(c)[1]["current_hash"]
    g4(c)
    set_lot(c, bid_count=2, final_hash=second)


def g6(c: Case) -> None:
    set_lot(c, bid_count=2)


def g7(c: Case) -> None:
    set_lot(c, final_hash=OTHER_HASH)


def g8_empty(c: Case) -> None:  # âncora vazia de outro lote
    other = live_lot(c.factory)
    stolen = lot_state(c.factory, other)["anchor_hmac"]
    set_lot(c, anchor_hmac=stolen)


def g8_filled(c: Case) -> None:  # âncora de outro lote com lances
    other = chained_lot(c.factory)
    stolen = lot_state(c.factory, other)["anchor_hmac"]
    set_lot(c, anchor_hmac=stolen)


def g9_filled(c: Case) -> None:
    set_lot(c, anchor_hmac=None)


def g10(c: Case) -> None:
    set_lot(c, current_leader_id=BOB)


def g11(c: Case) -> None:
    set_lot(c, current_bid_cents=12_500)


def g12(c: Case) -> None:  # troca coordenada de líder e bidder_id do último lance
    set_lot(c, current_leader_id=BOB)
    tamper(
        c.factory,
        "UPDATE bids SET bidder_id = :bob WHERE lot_id = :id AND sequence = 3",
        id=c.lot_id,
        bob=BOB,
    )


def g13(c: Case) -> None:  # lance extra válido no fim, sem atualizar o lote
    # Os três primeiros lances saem idênticos (mesmas entradas, mesmos horários); o
    # quarto é novo e encadeado a eles. O lote continua dizendo "3 lances".
    rebuild(
        c.factory,
        c.lot_id,
        [(ALICE, 10_000), (BOB, 11_000), (ALICE, 12_000), (BOB, 13_000)],
        base=original(c),
    )


def g14(c: Case) -> None:
    c.drop("ck_lots_anchor_hmac_format")
    set_lot(c, anchor_hmac="xyz")


def g16(c: Case) -> None:  # bid_count > 0 sem lance atual nem líder
    c.drop("ck_lots_current_bid_with_leader", "ck_lots_bid_count_matches_current_bid")
    set_lot(c, current_bid_cents=None, current_leader_id=None)


def g17_version(c: Case) -> None:
    c.drop("ck_bids_canonical_version")
    tamper(
        c.factory,
        "UPDATE bids SET canonical_version = 2 WHERE lot_id = :id AND sequence = 2",
        id=c.lot_id,
    )


def g17_alias(c: Case) -> None:
    c.drop("ck_bids_bidder_alias_format")
    tamper(
        c.factory,
        "UPDATE bids SET bidder_alias = 'anonimo' WHERE lot_id = :id AND sequence = 2",
        id=c.lot_id,
    )


def g19(c: Case) -> None:  # inserção no meio, renumerada e recalculada
    base = original(c)
    final = rebuild(
        c.factory,
        c.lot_id,
        [(ALICE, 10_000), (BOB, 10_500), (BOB, 11_000), (ALICE, 12_000)],
        base=base,
    )
    set_lot(c, bid_count=4, final_hash=final)


def g20(c: Case) -> None:  # remoção do meio, sem renumerar
    tamper(
        c.factory, "DELETE FROM bids WHERE lot_id = :id AND sequence = 2", id=c.lot_id
    )


def g21(c: Case) -> None:  # remoção do meio, renumerada e recalculada
    base = original(c)
    final = rebuild(c.factory, c.lot_id, [(ALICE, 10_000), (ALICE, 12_000)], base=base)
    set_lot(c, bid_count=2, final_hash=final)


def g22(c: Case) -> None:  # só o bidder_id do último lance
    tamper(
        c.factory,
        "UPDATE bids SET bidder_id = :bob WHERE lot_id = :id AND sequence = 3",
        id=c.lot_id,
        bob=BOB,
    )


def g23(c: Case) -> None:  # âncora coerente, assinada com outro segredo de auditoria
    state = lot_state(c.factory, c.lot_id)
    forged = compute_anchor_hmac(
        AnchorState(
            v=1,
            lot_id=c.lot_id,
            bid_count=state["bid_count"],
            final_hash=state["final_hash"],
        ),
        audit_hmac_secret=integrity_secrets()[1],
    )
    set_lot(c, anchor_hmac=forged)


CASES = [
    pytest.param(g1, F.CHAIN_MISMATCH, id="G1-amount-changed"),
    pytest.param(
        g2, F.ANCHOR_MISMATCH, id="G2-recalculated-chain-new-summary-old-hmac"
    ),
    pytest.param(g3, F.SUMMARY_MISMATCH, id="G3-recalculated-chain-old-summary"),
    pytest.param(g4, F.SUMMARY_MISMATCH, id="G4-last-bid-deleted"),
    pytest.param(g5, F.ANCHOR_MISMATCH, id="G5-last-deleted-summary-adjusted"),
    pytest.param(g6, F.ANCHOR_MISMATCH, id="G6-only-bid-count"),
    pytest.param(g7, F.ANCHOR_MISMATCH, id="G7-only-final-hash"),
    pytest.param(g8_empty, F.ANCHOR_MISMATCH, id="G8-anchor-of-an-empty-other-lot"),
    pytest.param(g8_filled, F.ANCHOR_MISMATCH, id="G8-anchor-of-another-filled-lot"),
    pytest.param(g9_filled, F.MISSING_ANCHOR, id="G9-null-anchor-with-bids"),
    pytest.param(g10, F.OPERATIONAL_MISMATCH, id="G10-leader-swapped"),
    pytest.param(g11, F.OPERATIONAL_MISMATCH, id="G11-current-bid-swapped"),
    pytest.param(g12, F.OPERATIONAL_MISMATCH, id="G12-leader-and-bidder-id-swapped"),
    pytest.param(g13, F.SUMMARY_MISMATCH, id="G13-extra-valid-bid-at-the-end"),
    pytest.param(g14, F.MALFORMED_STATE, id="G14-anchor-format-check-removed"),
    pytest.param(g16, F.OPERATIONAL_MISMATCH, id="G16-count-without-current-bid"),
    pytest.param(g17_version, F.MALFORMED_STATE, id="G17-canonical-version-2"),
    pytest.param(g17_alias, F.MALFORMED_STATE, id="G17-malformed-alias"),
    pytest.param(g19, F.ANCHOR_MISMATCH, id="G19-insertion-in-the-middle"),
    pytest.param(g20, F.CHAIN_MISMATCH, id="G20-middle-removed-no-renumbering"),
    pytest.param(g21, F.ANCHOR_MISMATCH, id="G21-middle-removed-renumbered"),
    pytest.param(g22, F.OPERATIONAL_MISMATCH, id="G22-only-last-bidder-id"),
    pytest.param(g23, F.ANCHOR_MISMATCH, id="G23-anchor-with-another-audit-secret"),
]


def attempt(
    client: TestClient,
    factory: sessionmaker[Session],
    engine: Engine,
    caplog: pytest.LogCaptureFixture,
    lot_id: uuid.UUID,
    amount: int,
) -> Any:
    with (
        caplog.at_level(logging.INFO, logger="uvicorn.error"),
        statement_log(engine) as log,
    ):
        response = client.post(
            f"/api/lots/{lot_id}/bids",
            json={"amount_cents": amount},
            headers=json_headers(HTTPS_ORIGIN),
        )
    response.statement_log = log  # type: ignore[attr-defined]
    return response


def assert_conflict(
    response: Any, caplog: pytest.LogCaptureFixture, lot_id: uuid.UUID, reason: F
) -> None:
    assert response.status_code == 409
    assert response.json() == INTEGRITY_BODY  # idêntico para toda categoria
    assert response.headers["cache-control"] == "no-store"
    assert not response.statement_log.saw("FROM wallets")  # nenhuma carteira travada
    trace = service_trace(response.statement_log)
    assert trace == ["lock_lot", "clock", "history"]  # parou no gate: nenhuma escrita
    messages = [r.getMessage() for r in caplog.records if r.name == "uvicorn.error"]
    assert messages == [
        f"bid refused: integrity conflict lot_id={lot_id} reason={reason.value}"
    ]
    for secret in integrity_secrets():
        assert secret.decode() not in caplog.text + response.text
    assert "Licitante-" not in caplog.text + response.text


@pytest.mark.parametrize(("tamper_with", "reason"), CASES)
def test_a_legitimate_bid_after_any_tampering_is_a_409_with_no_effect(
    seeded: sessionmaker[Session],
    bob_client: TestClient,
    db_engine: Engine,
    drop_checks: Callable[..., None],  # noqa: F811
    caplog: pytest.LogCaptureFixture,
    tamper_with: Callable[[Case], None],
    reason: F,
) -> None:
    case = Case(seeded, chained_lot(seeded), drop_checks)
    tamper_with(case)
    before = db_snapshot(seeded)

    response = attempt(bob_client, seeded, db_engine, caplog, case.lot_id, 13_000)

    assert_conflict(response, caplog, case.lot_id, reason)
    assert db_snapshot(seeded) == before  # nenhuma HMAC nova, nada reparado


def test_g9_null_anchor_on_an_empty_signed_lot_and_on_a_legacy_lot(
    seeded: sessionmaker[Session],
    bob_client: TestClient,
    db_engine: Engine,
    caplog: pytest.LogCaptureFixture,
) -> None:
    for lot_id in (
        live_lot(seeded, anchored=False),  # legado
        live_lot(seeded, anchor_hmac=None),  # assinado e depois apagado
    ):
        before = db_snapshot(seeded)
        caplog.clear()
        response = attempt(bob_client, seeded, db_engine, caplog, lot_id, 10_000)
        assert_conflict(response, caplog, lot_id, F.MISSING_ANCHOR)
        assert db_snapshot(seeded) == before


def test_g15_an_empty_lot_with_a_leader_and_a_current_bid(
    seeded: sessionmaker[Session],
    bob_client: TestClient,
    db_engine: Engine,
    drop_checks: Callable[..., None],  # noqa: F811
    caplog: pytest.LogCaptureFixture,
) -> None:
    lot_id = live_lot(seeded, starting_bid_cents=10_000)
    drop_checks(
        "ck_lots_current_bid_with_leader", "ck_lots_bid_count_matches_current_bid"
    )
    tamper(
        seeded,
        "UPDATE lots SET current_bid_cents = 10000, current_leader_id = :alice "
        "WHERE id = :id",
        id=lot_id,
        alice=ALICE,
    )
    before = db_snapshot(seeded)

    response = attempt(bob_client, seeded, db_engine, caplog, lot_id, 11_000)

    assert_conflict(response, caplog, lot_id, F.OPERATIONAL_MISMATCH)
    assert db_snapshot(seeded) == before


def test_g8_an_empty_lot_cannot_use_the_anchor_of_another_empty_lot(
    seeded: sessionmaker[Session],
    bob_client: TestClient,
    db_engine: Engine,
    caplog: pytest.LogCaptureFixture,
) -> None:
    lot_id, other = live_lot(seeded), live_lot(seeded)
    tamper(
        seeded,
        "UPDATE lots SET anchor_hmac = (SELECT anchor_hmac FROM lots WHERE id = :o) "
        "WHERE id = :id",
        id=lot_id,
        o=other,
    )
    before = db_snapshot(seeded)

    response = attempt(bob_client, seeded, db_engine, caplog, lot_id, 10_000)

    assert_conflict(response, caplog, lot_id, F.ANCHOR_MISMATCH)
    assert db_snapshot(seeded) == before


# --- G18: ValueError fora do gate é 500, nunca 409 ---


def test_g18_inconsistent_lot_terms_are_a_500_and_not_a_409(
    seeded: sessionmaker[Session],
    bob_client: TestClient,
    db_engine: Engine,
    drop_checks: Callable[..., None],  # noqa: F811
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Os termos do lote não são cobertos pela âncora v1: o gate passa e `LotBidState`
    levanta. Captura ampla de `ValueError` esconderia esse bug como 409."""
    lot_id = chained_lot(seeded)
    drop_checks("ck_lots_current_bid_at_least_starting")
    tamper(
        seeded, "UPDATE lots SET starting_bid_cents = 50000 WHERE id = :id", id=lot_id
    )
    before = db_snapshot(seeded)

    response = attempt(bob_client, seeded, db_engine, caplog, lot_id, 60_000)

    assert response.status_code == 500
    assert response.json()["code"] == "internal_error"
    assert db_snapshot(seeded) == before


# --- SR-01: 409 tem prioridade sobre as recusas de negócio ---


def test_g9b_a_legacy_lot_that_already_ended_is_a_409_and_not_lot_ended(
    seeded: sessionmaker[Session],
    bob_client: TestClient,
    db_engine: Engine,
    caplog: pytest.LogCaptureFixture,
) -> None:
    now = db_now(seeded)
    lot_id = live_lot(
        seeded,
        anchored=False,
        starts_at=now - timedelta(hours=2),
        ends_at=now - timedelta(hours=1),
    )
    before = db_snapshot(seeded)

    response = attempt(bob_client, seeded, db_engine, caplog, lot_id, 10_000)

    assert_conflict(response, caplog, lot_id, F.MISSING_ANCHOR)
    assert db_snapshot(seeded) == before


def test_g10b_a_swapped_leader_that_is_the_bidder_is_a_409_and_not_already_winning(
    seeded: sessionmaker[Session],
    bob_client: TestClient,
    db_engine: Engine,
    caplog: pytest.LogCaptureFixture,
) -> None:
    lot_id = live_lot(seeded, starting_bid_cents=10_000)
    assert isinstance(run_bid(seeded, lot_id, ALICE, 10_000), PlacedBid)
    tamper(
        seeded,
        "UPDATE lots SET current_leader_id = :bob WHERE id = :id",
        id=lot_id,
        bob=BOB,
    )
    before = db_snapshot(seeded)

    response = attempt(bob_client, seeded, db_engine, caplog, lot_id, 11_000)

    assert_conflict(response, caplog, lot_id, F.OPERATIONAL_MISMATCH)
    assert db_snapshot(seeded) == before


def test_g11b_an_inflated_current_bid_is_a_409_and_not_below_minimum(
    seeded: sessionmaker[Session],
    bob_client: TestClient,
    db_engine: Engine,
    caplog: pytest.LogCaptureFixture,
) -> None:
    lot_id = live_lot(seeded, starting_bid_cents=10_000)
    assert isinstance(run_bid(seeded, lot_id, ALICE, 10_000), PlacedBid)
    tamper(
        seeded,
        "UPDATE lots SET current_bid_cents = 20000 WHERE id = :id",
        id=lot_id,
    )
    before = db_snapshot(seeded)

    # Sem o gate, 11 000 < 20 000 + 1 000 seria `below_minimum` (422).
    response = attempt(bob_client, seeded, db_engine, caplog, lot_id, 11_000)

    assert_conflict(response, caplog, lot_id, F.OPERATIONAL_MISMATCH)
    assert db_snapshot(seeded) == before


# --- o serviço devolve a categoria; a rota esconde ---


def test_the_service_reports_the_category_for_every_lot_state(
    seeded: sessionmaker[Session],
) -> None:
    lot_id = chained_lot(seeded)
    tamper(
        seeded,
        "UPDATE lots SET final_hash = :h WHERE id = :id",
        id=lot_id,
        h=OTHER_HASH,
    )

    result = run_bid(seeded, lot_id, BOB, 13_000)

    assert result == IntegrityConflict(F.ANCHOR_MISMATCH)


def test_a_clean_chained_lot_still_accepts_the_legitimate_bid(
    seeded: sessionmaker[Session],
    bob_client: TestClient,
    db_engine: Engine,
    caplog: pytest.LogCaptureFixture,
) -> None:
    lot_id = chained_lot(seeded)

    response = attempt(bob_client, seeded, db_engine, caplog, lot_id, 13_000)

    assert response.status_code == 201
    assert response.json()["bid"]["sequence"] == 4


# --- drop_checks (N-02, D17) ---


def test_drop_checks_refuses_constraints_outside_lots_and_bids_before_dropping_any(
    db_engine: Engine,
    drop_checks: Callable[..., None],  # noqa: F811
) -> None:
    def present(names: list[str]) -> dict[str, Any]:
        with db_engine.connect() as connection:
            found = read_checks(connection, names)
            connection.rollback()
        return found

    names = ["ck_wallets_total_range", "ck_users_role", "ck_lots_ends_after_starts"]
    before = present(names)

    with pytest.raises(AssertionError, match="fora de lots e bids"):
        drop_checks("ck_lots_ends_after_starts", "ck_wallets_total_range")
    with pytest.raises(AssertionError, match="fora de lots e bids"):
        drop_checks("ck_users_role")
    with pytest.raises(AssertionError, match="inexistente"):
        drop_checks("ck_lots_nao_existe")

    assert present(names) == before  # nem a de `lots` (a mista) foi removida


def test_drop_checks_removes_only_what_was_asked_and_the_fixture_restores_it(
    db_engine: Engine,
    drop_checks: Callable[..., None],  # noqa: F811
) -> None:
    names = ["ck_lots_anchor_hmac_format", "ck_bids_canonical_version"]
    with db_engine.connect() as connection:
        before = read_checks(connection, names)
        remaining = read_checks(connection, ["ck_lots_ends_after_starts"])
        connection.rollback()
    assert len(before) == 2 and before["ck_bids_canonical_version"].table == "bids"
    assert before["ck_lots_anchor_hmac_format"].definition.startswith("CHECK")

    drop_checks(*names)

    with db_engine.connect() as connection:
        assert read_checks(connection, names) == {}
        assert read_checks(connection, ["ck_lots_ends_after_starts"]) == remaining
        connection.rollback()
    # O finalizador da fixture recria as duas com a definição capturada e confere o
    # catálogo; o teste abaixo olha o resultado depois dele.


def test_the_catalog_has_every_check_again_after_the_drop_tests(
    db_engine: Engine,
) -> None:
    names = [
        "ck_lots_anchor_hmac_format",
        "ck_bids_canonical_version",
        "ck_bids_bidder_alias_format",
        "ck_lots_current_bid_with_leader",
        "ck_lots_bid_count_matches_current_bid",
        "ck_lots_current_bid_at_least_starting",
    ]
    with db_engine.connect() as connection:
        found = read_checks(connection, names)
        connection.rollback()
    assert sorted(found) == sorted(names)
