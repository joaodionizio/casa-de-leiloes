"""O gate que autentica o estado anterior, sem banco (Story 3.4, D3, CAP-2).

`authenticate_previous_state` recebe objetos simples: cada categoria de falha, a ordem
em que elas são avaliadas e o limite do `try/except ValueError`."""

import uuid
from dataclasses import replace
from datetime import UTC, datetime, timedelta
from types import SimpleNamespace
from typing import Any

import pytest

from app import bids
from app.bid_integrity import (
    GENESIS_HASH,
    AnchorState,
    CanonicalBid,
    compute_anchor_hmac,
    compute_bid_hash,
    generate_bidder_alias,
)
from app.bid_rules import CurrentBid
from app.bids import (
    AuthenticatedLot,
    IntegrityConflict,
    IntegrityFailure,
    authenticate_previous_state,
)
from app.config import IntegrityConfig

AUDIT = b"a" * 32
PSEUDONYM = b"p" * 32
INTEGRITY = IntegrityConfig(audit_hmac_secret=AUDIT, pseudonym_secret=PSEUDONYM)
LOT_ID = uuid.UUID("11111111-1111-4111-8111-111111111111")
USER_A = uuid.UUID("aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa")
USER_B = uuid.UUID("bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb")
START = datetime(2026, 10, 26, 12, 0, 0, 123456, tzinfo=UTC)


def sign(count: int, final_hash: str, lot_id: uuid.UUID = LOT_ID) -> str:
    return compute_anchor_hmac(
        AnchorState(v=1, lot_id=lot_id, bid_count=count, final_hash=final_hash),
        audit_hmac_secret=AUDIT,
    )


def chain(users: list[uuid.UUID], lot_id: uuid.UUID = LOT_ID) -> list[SimpleNamespace]:
    """Lances encadeados e válidos; o lance `i` é de `users[i]`, de `10_000 * (i+1)`."""
    rows: list[SimpleNamespace] = []
    previous = GENESIS_HASH
    for index, user in enumerate(users):
        alias = generate_bidder_alias(
            lot_id=lot_id, user_id=user, pseudonym_secret=PSEUDONYM
        )
        placed_at = START + timedelta(seconds=index)
        canonical = CanonicalBid(
            v=1,
            lot_id=lot_id,
            sequence=index + 1,
            bidder_alias=alias,
            amount_cents=10_000 * (index + 1),
            timestamp=placed_at,
            previous_hash=previous,
        )
        current = compute_bid_hash(canonical)
        rows.append(
            SimpleNamespace(
                lot_id=lot_id,
                sequence=index + 1,
                bidder_id=user,
                bidder_alias=alias,
                amount_cents=canonical.amount_cents,
                placed_at=placed_at,
                previous_hash=previous,
                current_hash=current,
                canonical_version=1,
            )
        )
        previous = current
    return rows


def lot_for(rows: list[SimpleNamespace], **overrides: Any) -> SimpleNamespace:
    """O lote coerente com `rows`, assinado com o segredo de auditoria."""
    final = rows[-1].current_hash if rows else GENESIS_HASH
    values: dict[str, Any] = {
        "anchor_hmac": sign(len(rows), final),
        "bid_count": len(rows),
        "final_hash": final,
        "current_bid_cents": rows[-1].amount_cents if rows else None,
        "current_leader_id": rows[-1].bidder_id if rows else None,
    }
    values.update(overrides)
    return SimpleNamespace(**values)


def gate(lot: Any, rows: list[Any]) -> AuthenticatedLot | IntegrityConflict:
    return authenticate_previous_state(lot, rows, integrity=INTEGRITY, lot_id=LOT_ID)


def conflict(reason: IntegrityFailure) -> IntegrityConflict:
    return IntegrityConflict(reason)


# --- caminho feliz ---


def test_an_empty_signed_lot_is_authenticated_with_no_current_bid() -> None:
    assert gate(lot_for([]), []) == AuthenticatedLot(
        bid_count=0, final_hash=GENESIS_HASH, current=None
    )


def test_a_lot_with_a_valid_chain_returns_the_authenticated_summary_and_leader() -> (
    None
):
    rows = chain([USER_A, USER_B, USER_A])

    result = gate(lot_for(rows), rows)

    assert result == AuthenticatedLot(
        bid_count=3,
        final_hash=rows[-1].current_hash,
        current=CurrentBid(amount_cents=30_000, leader_id=USER_A),
    )


def test_the_gate_does_not_change_the_lot_or_the_rows() -> None:
    rows = chain([USER_A, USER_B])
    lot = lot_for(rows)
    before = (vars(lot).copy(), [vars(row).copy() for row in rows])

    gate(lot, rows)

    assert (vars(lot), [vars(row) for row in rows]) == before


def test_only_the_alias_of_the_current_leader_is_recomputed(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    rows = chain([USER_A, USER_B, USER_A, USER_B])
    lot = lot_for(rows)
    calls: list[uuid.UUID] = []
    real = bids.generate_bidder_alias

    def spy(**kwargs: Any) -> str:
        calls.append(kwargs["user_id"])
        return real(**kwargs)

    monkeypatch.setattr(bids, "generate_bidder_alias", spy)

    assert isinstance(gate(lot, rows), AuthenticatedLot)
    assert calls == [USER_B]  # nenhum alias histórico


# --- cada categoria ---


@pytest.mark.parametrize("count", [0, 2])
def test_a_missing_anchor_is_never_trusted(count: int) -> None:
    rows = chain([USER_A, USER_B][:count])

    result = gate(lot_for(rows, anchor_hmac=None), rows)

    assert result == conflict(IntegrityFailure.MISSING_ANCHOR)


def test_a_changed_bid_breaks_the_chain() -> None:
    rows = chain([USER_A, USER_B])
    rows[0].amount_cents = 99_999

    assert gate(lot_for(rows), rows) == conflict(IntegrityFailure.CHAIN_MISMATCH)


def test_a_gap_in_the_sequence_breaks_the_chain() -> None:
    rows = chain([USER_A, USER_B, USER_A])
    del rows[1]

    assert gate(lot_for(rows), rows) == conflict(IntegrityFailure.CHAIN_MISMATCH)


def test_an_anchor_signed_with_another_secret_does_not_match() -> None:
    rows = chain([USER_A])
    forged = compute_anchor_hmac(
        AnchorState(v=1, lot_id=LOT_ID, bid_count=1, final_hash=rows[-1].current_hash),
        audit_hmac_secret=PSEUDONYM,
    )

    assert gate(lot_for(rows, anchor_hmac=forged), rows) == conflict(
        IntegrityFailure.ANCHOR_MISMATCH
    )


def test_an_anchor_copied_from_another_lot_does_not_match() -> None:
    other = uuid.uuid4()
    foreign_empty = sign(0, GENESIS_HASH, lot_id=other)
    rows = chain([USER_A])
    foreign_filled = sign(1, rows[-1].current_hash, lot_id=other)

    assert gate(lot_for([], anchor_hmac=foreign_empty), []) == conflict(
        IntegrityFailure.ANCHOR_MISMATCH
    )
    assert gate(lot_for(rows, anchor_hmac=foreign_filled), rows) == conflict(
        IntegrityFailure.ANCHOR_MISMATCH
    )


def test_a_valid_chain_of_another_lot_does_not_authenticate_this_one() -> None:
    other = uuid.uuid4()
    rows = chain([USER_A], lot_id=other)

    result = gate(lot_for(rows), rows)

    assert result == conflict(IntegrityFailure.CHAIN_MISMATCH)


def test_a_signed_summary_that_disagrees_with_the_chain_is_a_summary_mismatch() -> None:
    rows = chain([USER_A, USER_B])
    # Âncora válida para (3, hash qualquer): HMAC e cadeia passam, o resumo não.
    fake_hash = "f" * 64
    lot = lot_for(
        rows, bid_count=3, final_hash=fake_hash, anchor_hmac=sign(3, fake_hash)
    )

    assert gate(lot, rows) == conflict(IntegrityFailure.SUMMARY_MISMATCH)


def test_a_truncated_history_is_a_summary_mismatch() -> None:
    rows = chain([USER_A, USER_B])
    lot = lot_for(rows)  # âncora, contagem e hash final de 2 lances

    # O último lance sumiu: a cadeia restante é válida e a âncora confere com o lote,
    # mas o resumo assinado fala de 2 lances.
    assert gate(lot, rows[:1]) == conflict(IntegrityFailure.SUMMARY_MISMATCH)


@pytest.mark.parametrize(
    "overrides",
    [
        {"current_leader_id": USER_A},  # troca o líder
        {"current_bid_cents": 20_001},  # troca o lance atual
        {"current_leader_id": None},
        {"current_bid_cents": None},
    ],
)
def test_the_current_leader_and_bid_must_be_the_last_bid(
    overrides: dict[str, Any],
) -> None:
    rows = chain([USER_A, USER_B])

    result = gate(lot_for(rows, **overrides), rows)

    assert result == conflict(IntegrityFailure.OPERATIONAL_MISMATCH)


def test_swapping_the_last_bidder_id_and_the_leader_together_hits_the_alias() -> None:
    rows = chain([USER_A, USER_B])
    rows[-1].bidder_id = USER_A

    result = gate(lot_for(rows, current_leader_id=USER_A), rows)

    assert result == conflict(IntegrityFailure.OPERATIONAL_MISMATCH)


def test_swapping_only_the_last_bidder_id_is_caught_by_the_leader_link() -> None:
    rows = chain([USER_A, USER_B])
    rows[-1].bidder_id = USER_A

    assert gate(lot_for(rows), rows) == conflict(IntegrityFailure.OPERATIONAL_MISMATCH)


@pytest.mark.parametrize(
    "overrides",
    [{"current_leader_id": USER_A}, {"current_bid_cents": 10_000}],
)
def test_an_empty_lot_cannot_have_a_leader_or_a_current_bid(
    overrides: dict[str, Any],
) -> None:
    assert gate(lot_for([], **overrides), []) == conflict(
        IntegrityFailure.OPERATIONAL_MISMATCH
    )


# --- ValueError estrutural vira 409; o resto não ---


@pytest.mark.parametrize(
    "mutate",
    [
        lambda row: setattr(row, "canonical_version", 2),
        lambda row: setattr(row, "bidder_alias", "Licitante-minusculo0000"),
        lambda row: setattr(row, "placed_at", START.replace(tzinfo=None)),
        lambda row: setattr(row, "sequence", 0),
        lambda row: setattr(row, "amount_cents", 0),
        lambda row: setattr(row, "previous_hash", "XYZ"),
        lambda row: setattr(row, "current_hash", "XYZ"),
    ],
    ids=["version", "alias", "naive-time", "sequence", "amount", "prev", "hash"],
)
def test_a_structurally_invalid_row_is_a_malformed_state(mutate: Any) -> None:
    rows = chain([USER_A])
    lot = lot_for(rows)
    mutate(rows[0])

    assert gate(lot, rows) == conflict(IntegrityFailure.MALFORMED_STATE)


@pytest.mark.parametrize(
    "overrides",
    [
        {"anchor_hmac": "não é hexadecimal"},
        {"bid_count": -1},
        {"final_hash": "XYZ"},
        {"bid_count": 0, "final_hash": "f" * 64},  # vazio com hash que não é genesis
    ],
)
def test_a_structurally_invalid_lot_is_a_malformed_state(
    overrides: dict[str, Any],
) -> None:
    assert gate(lot_for([], **overrides), []) == conflict(
        IntegrityFailure.MALFORMED_STATE
    )


def test_an_error_that_is_not_a_value_error_is_not_swallowed() -> None:
    class Exploding(SimpleNamespace):
        @property
        def canonical_version(self) -> int:
            raise RuntimeError("bug")

    rows = chain([USER_A])
    broken = Exploding(
        **{k: v for k, v in vars(rows[0]).items() if k != "canonical_version"}
    )

    with pytest.raises(RuntimeError):
        gate(lot_for(rows), [broken])


# --- ordem das categorias ---


def test_missing_anchor_is_evaluated_before_everything_else() -> None:
    rows = chain([USER_A, USER_B])
    rows[0].amount_cents = 1  # cadeia quebrada também

    result = gate(lot_for(rows, anchor_hmac=None, current_leader_id=USER_A), rows)

    assert result == conflict(IntegrityFailure.MISSING_ANCHOR)


def test_a_malformed_row_wins_over_a_chain_mismatch() -> None:
    rows = chain([USER_A, USER_B])
    lot = lot_for(rows)
    rows[0].amount_cents = 1  # cadeia quebrada
    rows[1].canonical_version = 2  # estrutura inválida

    assert gate(lot, rows) == conflict(IntegrityFailure.MALFORMED_STATE)


def test_chain_mismatch_wins_over_anchor_and_summary_and_operational() -> None:
    rows = chain([USER_A, USER_B])
    lot = lot_for(rows, anchor_hmac=sign(0, GENESIS_HASH), current_leader_id=USER_A)
    rows[0].amount_cents = 1

    assert gate(lot, rows) == conflict(IntegrityFailure.CHAIN_MISMATCH)


def test_anchor_mismatch_wins_over_summary_and_operational() -> None:
    rows = chain([USER_A, USER_B])
    lot = lot_for(
        rows, anchor_hmac=sign(0, GENESIS_HASH), bid_count=5, current_leader_id=USER_A
    )

    assert gate(lot, rows) == conflict(IntegrityFailure.ANCHOR_MISMATCH)


def test_summary_mismatch_wins_over_operational() -> None:
    rows = chain([USER_A, USER_B])
    fake_hash = "e" * 64
    lot = lot_for(
        rows,
        bid_count=9,
        final_hash=fake_hash,
        anchor_hmac=sign(9, fake_hash),
        current_leader_id=USER_A,
    )

    assert gate(lot, rows) == conflict(IntegrityFailure.SUMMARY_MISMATCH)


def test_the_conflict_carries_only_the_category() -> None:
    result = gate(lot_for([], anchor_hmac=None), [])

    assert isinstance(result, IntegrityConflict)
    assert vars(result) == {"reason": IntegrityFailure.MISSING_ANCHOR}
    assert replace(result, reason=IntegrityFailure.CHAIN_MISMATCH).reason is (
        IntegrityFailure.CHAIN_MISMATCH
    )
