"""Integridade histórica v1, pura e independente de persistência (Story 3.3).

A cadeia prova coerência interna. Seu consumidor precisa autenticar a âncora
anterior e vinculá-la ao lote, count e hash observados antes de qualquer extensão;
ver integrity-contract §9. Segredos e instantes são sempre entradas explícitas.
"""

import hashlib
import hmac
import json
import re
from dataclasses import dataclass
from datetime import UTC, datetime
from uuid import UUID

from app.lot_time import require_aware
from app.money import MAX_CENTS

GENESIS_HASH = "0" * 64
_MISSING = object()


def _uuid(name: str, value: object) -> None:
    if not isinstance(value, UUID):
        raise ValueError(f"{name} must be a UUID")


def _integer(
    name: str, value: object, minimum: int, maximum: int | None = None
) -> None:
    if type(value) is not int:
        raise ValueError(f"{name} must be an integer")
    if value < minimum or (maximum is not None and value > maximum):
        raise ValueError(f"{name} out of range")


def _hash(name: str, value: object) -> None:
    if type(value) is not str or re.fullmatch(r"[0-9a-f]{64}", value) is None:
        raise ValueError(f"{name} must be 64 lowercase hexadecimal characters")


def _secret(name: str, value: object) -> None:
    if type(value) is not bytes or not value:
        raise ValueError(f"{name} must be non-empty bytes")


@dataclass(frozen=True, kw_only=True, init=False)
class CanonicalBid:
    v: int
    lot_id: UUID
    sequence: int
    bidder_alias: str
    amount_cents: int
    timestamp: datetime
    previous_hash: str

    def __init__(
        self,
        *,
        v=_MISSING,
        lot_id=_MISSING,
        sequence=_MISSING,
        bidder_alias=_MISSING,
        amount_cents=_MISSING,
        timestamp=_MISSING,
        previous_hash=_MISSING,
        **unexpected,
    ):
        if unexpected:
            raise ValueError("unexpected fields")
        _integer("v", v, 1, 1)
        _uuid("lot_id", lot_id)
        _integer("sequence", sequence, 1)
        if (
            type(bidder_alias) is not str
            or re.fullmatch(r"Licitante-[0-9A-F]{16}", bidder_alias) is None
        ):
            raise ValueError("bidder_alias must match the v1 alias format")
        _integer("amount_cents", amount_cents, 1, MAX_CENTS)
        try:
            timestamp_utc = require_aware("timestamp", timestamp).astimezone(UTC)
        except (OverflowError, TypeError, ValueError) as error:
            raise ValueError(
                "timestamp must be representable in UTC and timezone-aware"
            ) from error
        _hash("previous_hash", previous_hash)
        object.__setattr__(self, "v", v)
        object.__setattr__(self, "lot_id", lot_id)
        object.__setattr__(self, "sequence", sequence)
        object.__setattr__(self, "bidder_alias", bidder_alias)
        object.__setattr__(self, "amount_cents", amount_cents)
        object.__setattr__(self, "timestamp", timestamp_utc)
        object.__setattr__(self, "previous_hash", previous_hash)


@dataclass(frozen=True, kw_only=True, init=False)
class AnchorState:
    v: int
    lot_id: UUID
    bid_count: int
    final_hash: str

    def __init__(
        self,
        *,
        v=_MISSING,
        lot_id=_MISSING,
        bid_count=_MISSING,
        final_hash=_MISSING,
        **unexpected,
    ):
        if unexpected:
            raise ValueError("unexpected fields")
        _integer("v", v, 1, 1)
        _uuid("lot_id", lot_id)
        _integer("bid_count", bid_count, 0)
        _hash("final_hash", final_hash)
        if bid_count == 0 and final_hash != GENESIS_HASH:
            raise ValueError("final_hash must be genesis when bid_count is zero")
        object.__setattr__(self, "v", v)
        object.__setattr__(self, "lot_id", lot_id)
        object.__setattr__(self, "bid_count", bid_count)
        object.__setattr__(self, "final_hash", final_hash)


@dataclass(frozen=True, kw_only=True, init=False)
class VerifiableBid:
    bid: CanonicalBid
    current_hash: str

    def __init__(self, *, bid=_MISSING, current_hash=_MISSING, **unexpected):
        if unexpected:
            raise ValueError("unexpected fields")
        if not isinstance(bid, CanonicalBid):
            raise ValueError("bid must be a CanonicalBid")
        _hash("current_hash", current_hash)
        object.__setattr__(self, "bid", bid)
        object.__setattr__(self, "current_hash", current_hash)


def generate_bidder_alias(
    *, lot_id: UUID, user_id: UUID, pseudonym_secret: bytes
) -> str:
    _uuid("lot_id", lot_id)
    _uuid("user_id", user_id)
    _secret("pseudonym_secret", pseudonym_secret)
    message = f"{str(lot_id)}:{str(user_id)}".encode("utf-8")  # noqa: UP012
    digest = hmac.new(pseudonym_secret, message, hashlib.sha256).hexdigest()
    return "Licitante-" + digest[:16].upper()


def _json_bytes(payload: dict) -> bytes:
    return json.dumps(
        payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False
    ).encode("utf-8")


def canonical_bid_bytes(bid: CanonicalBid) -> bytes:
    if not isinstance(bid, CanonicalBid):
        raise ValueError("bid must be a CanonicalBid")
    timestamp = (
        bid.timestamp.isoformat(timespec="microseconds").removesuffix("+00:00") + "Z"
    )
    return _json_bytes(
        {
            "v": bid.v,
            "lot_id": str(bid.lot_id),
            "sequence": bid.sequence,
            "bidder_alias": bid.bidder_alias,
            "amount_cents": bid.amount_cents,
            "timestamp": timestamp,
            "previous_hash": bid.previous_hash,
        }
    )


def compute_bid_hash(bid: CanonicalBid) -> str:
    return hashlib.sha256(canonical_bid_bytes(bid)).hexdigest()


def canonical_anchor_bytes(state: AnchorState) -> bytes:
    if not isinstance(state, AnchorState):
        raise ValueError("state must be an AnchorState")
    return _json_bytes(
        {
            "v": state.v,
            "lot_id": str(state.lot_id),
            "bid_count": state.bid_count,
            "final_hash": state.final_hash,
        }
    )


def compute_anchor_hmac(state: AnchorState, *, audit_hmac_secret: bytes) -> str:
    payload = canonical_anchor_bytes(state)
    _secret("audit_hmac_secret", audit_hmac_secret)
    return hmac.new(audit_hmac_secret, payload, hashlib.sha256).hexdigest()


def verify_anchor_hmac(
    state: AnchorState, signature: str, *, audit_hmac_secret: bytes
) -> bool:
    if not isinstance(state, AnchorState):
        raise ValueError("state must be an AnchorState")
    _hash("signature", signature)
    _secret("audit_hmac_secret", audit_hmac_secret)
    expected = compute_anchor_hmac(state, audit_hmac_secret=audit_hmac_secret)
    return hmac.compare_digest(expected, signature)


def verify_bid_chain(records: tuple[VerifiableBid, ...], *, lot_id: UUID) -> bool:
    _uuid("lot_id", lot_id)
    if not isinstance(records, tuple):
        raise ValueError("records must be a tuple of VerifiableBid")
    for record in records:
        if not isinstance(record, VerifiableBid):
            raise ValueError("records must contain only VerifiableBid")
    previous_hash = GENESIS_HASH
    sequence = 1
    for record in records:
        bid = record.bid
        if (
            bid.lot_id != lot_id
            or bid.sequence != sequence
            or bid.previous_hash != previous_hash
            or record.current_hash != compute_bid_hash(bid)
        ):
            return False
        previous_hash = record.current_hash
        sequence += 1
    return True
