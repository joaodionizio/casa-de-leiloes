"""Contrato puro da integridade v1; vetores literais independentes da spec."""

import dataclasses
import hashlib
import inspect
import json
import re
from datetime import UTC, date, datetime, timedelta, timezone, tzinfo
from types import SimpleNamespace
from uuid import UUID

import pytest

import app.bid_integrity as integrity
from app.bid_integrity import (
    GENESIS_HASH,
    AnchorState,
    CanonicalBid,
    VerifiableBid,
    canonical_anchor_bytes,
    canonical_bid_bytes,
    compute_anchor_hmac,
    compute_bid_hash,
    generate_bidder_alias,
    verify_anchor_hmac,
    verify_bid_chain,
)
from app.money import MAX_CENTS

LOT = UUID("12345678-1234-5678-9abc-def012345678")
OTHER_LOT = UUID("12345678-1234-5678-9abc-def012345679")
USER = UUID("87654321-4321-8765-abcd-0123456789ab")
PSEUDONYM_SECRET = b"atrio-test-pseudonym-v1"
AUDIT_SECRET = b"atrio-test-audit-v1"
NOW = datetime(2026, 10, 23, 4, 15, 30, 123456, tzinfo=UTC)
ALIAS = "Licitante-9374E0069A540CEC"
BID_HASH = "a2ee0d3f151b6fd530657539654b2e8064352fc0c3a8d0e5db0c4744f931a4ed"
BID_BYTES = (
    b'{"amount_cents":12000,"bidder_alias":"Licitante-9374E0069A540CEC","l'
    b'ot_id":"12345678-1234-5678-9abc-def012345678","previous_hash":"00000'
    b'00000000000000000000000000000000000000000000000000000000000","sequen'
    b'ce":1,"timestamp":"2026-10-23T04:15:30.123456Z","v":1}'
)
ANCHOR_BYTES = (
    b'{"bid_count":1,"final_hash":"a2ee0d3f151b6fd530657539654b2e8064352fc'
    b'0c3a8d0e5db0c4744f931a4ed","lot_id":"12345678-1234-5678-9abc-def0123'
    b'45678","v":1}'
)
EMPTY_BYTES = (
    b'{"bid_count":0,"final_hash":"000000000000000000000000000000000000000'
    b'0000000000000000000000000","lot_id":"12345678-1234-5678-9abc-def0123'
    b'45678","v":1}'
)
ANCHOR_HMAC = "fdba84b9b662b56a8495e68dd507a446a72e9801e228c337a1dcbc360494e0d5"
EMPTY_HMAC = "302910667af56824d35920407dcead2b941798b39b1100e006a27fc7289e73a4"


def bid(**changes):
    values = dict(
        v=1,
        lot_id=LOT,
        sequence=1,
        bidder_alias=ALIAS,
        amount_cents=12000,
        timestamp=NOW,
        previous_hash=GENESIS_HASH,
    )
    values.update(changes)
    return CanonicalBid(**values)


def state(**changes):
    values = dict(v=1, lot_id=LOT, bid_count=1, final_hash=BID_HASH)
    values.update(changes)
    return AnchorState(**values)


def chain(count=3):
    records = []
    previous = GENESIS_HASH
    for sequence in range(1, count + 1):
        current = bid(sequence=sequence, previous_hash=previous)
        previous = compute_bid_hash(current)
        records.append(VerifiableBid(bid=current, current_hash=previous))
    return tuple(records)


def summary(records, lot_id=LOT):
    return state(
        lot_id=lot_id,
        bid_count=len(records),
        final_hash=records[-1].current_hash if records else GENESIS_HASH,
    )


def authenticated(records, previous_state, signature, lot_id=LOT):
    # As duas verificações são avaliadas antes de combinar os resultados (§9).
    chain_ok = verify_bid_chain(records, lot_id=lot_id)
    hmac_ok = verify_anchor_hmac(
        previous_state, signature, audit_hmac_secret=AUDIT_SECRET
    )
    return (
        chain_ok
        and hmac_ok
        and previous_state.lot_id == lot_id
        and previous_state.bid_count == len(records)
        and previous_state.final_hash
        == (records[-1].current_hash if records else GENESIS_HASH)
    )


def extend(records, previous_state, signature, emitted, lot_id=LOT):
    if not authenticated(records, previous_state, signature, lot_id):
        return False
    next_bid = bid(
        lot_id=lot_id,
        sequence=previous_state.bid_count + 1,
        previous_hash=previous_state.final_hash,
    )
    next_records = (
        *records,
        VerifiableBid(bid=next_bid, current_hash=compute_bid_hash(next_bid)),
    )
    next_state = summary(next_records, lot_id)
    emitted.append(
        (
            next_records,
            next_state,
            compute_anchor_hmac(next_state, audit_hmac_secret=AUDIT_SECRET),
        )
    )
    return True


@pytest.mark.parametrize(
    "factory,fields",
    [
        (bid, "v lot_id sequence bidder_alias amount_cents timestamp previous_hash"),
        (state, "v lot_id bid_count final_hash"),
        (lambda: VerifiableBid(bid=bid(), current_hash=BID_HASH), "bid current_hash"),
    ],
)
def test_exact_fields_and_frozen_types(factory, fields):
    obj = factory()
    assert [f.name for f in dataclasses.fields(obj)] == fields.split()
    with pytest.raises(dataclasses.FrozenInstanceError):
        setattr(obj, fields.split()[0], None)
    values = {f.name: getattr(obj, f.name) for f in dataclasses.fields(obj)}
    for field in values:
        with pytest.raises(ValueError, match=field):
            type(obj)(**{k: v for k, v in values.items() if k != field})
    with pytest.raises(ValueError, match="unexpected"):
        type(obj)(**values, unexpected_private_field=USER)
    with pytest.raises(TypeError):
        type(obj)(*values.values())


@pytest.mark.parametrize(
    "factory,field,invalid",
    [
        (bid, "v", [0, 2, -1, True, False, 1.0, "1", None]),
        (state, "v", [0, 2, -1, True, False, 1.0, "1", None]),
        (bid, "sequence", [0, -1, True, False, 1.0, "1", None]),
        (bid, "amount_cents", [0, -1, MAX_CENTS + 1, True, False, 1.0, 1.5, "1", None]),
        (state, "bid_count", [-1, True, False, 1.0, "1", None]),
        (bid, "lot_id", [str(LOT), 1, None]),
        (state, "lot_id", [str(LOT), 1, None]),
    ],
)
def test_invalid_fields(factory, field, invalid):
    for value in invalid:
        with pytest.raises(ValueError, match=field):
            factory(**{field: value})


@pytest.mark.parametrize("value", [1, MAX_CENTS + 1, 2**100])
def test_counters_have_no_artificial_ceiling(value):
    assert bid(sequence=value).sequence == value
    assert state(bid_count=value).bid_count == value


@pytest.mark.parametrize("value", [1, MAX_CENTS])
def test_amount_boundaries(value):
    assert bid(amount_cents=value).amount_cents == value


def test_empty_anchor_invariant():
    assert state(bid_count=0, final_hash=GENESIS_HASH).bid_count == 0
    with pytest.raises(ValueError, match="final_hash"):
        state(bid_count=0)


@pytest.mark.parametrize(
    "value",
    [
        "",
        "licitante-9374E0069A540CEC",
        "Licitante-12345678",
        "Licitante-" + "A" * 15,
        "Licitante-" + "A" * 17,
        "Licitante-" + "a" * 16,
        "Licitante-" + "G" * 16,
        ALIAS + " ",
        ALIAS + "\n",
        ALIAS + "\x00",
        ALIAS.replace("L", "Ｌ"),
        b"alias",
        None,
    ],
)
def test_strict_alias(value):
    with pytest.raises(ValueError, match="bidder_alias"):
        bid(bidder_alias=value)


@pytest.mark.parametrize(
    "value",
    [
        "a" * 63,
        "a" * 65,
        "A" * 64,
        "g" * 64,
        "a" * 64 + "\n",
        " " + "a" * 64,
        b"a" * 64,
        None,
    ],
)
def test_strict_hashes(value):
    for factory, field in [
        (bid, "previous_hash"),
        (state, "final_hash"),
        (lambda **kw: VerifiableBid(bid=bid(), **kw), "current_hash"),
    ]:
        with pytest.raises(ValueError, match=field):
            factory(**{field: value})
    with pytest.raises(ValueError, match="signature"):
        verify_anchor_hmac(state(), value, audit_hmac_secret=AUDIT_SECRET)


@pytest.mark.parametrize(
    "secret", [b"", "private-marker", bytearray(b"x"), memoryview(b"x"), None]
)
def test_secrets(secret):
    for call, field in [
        (
            lambda: generate_bidder_alias(
                lot_id=LOT, user_id=USER, pseudonym_secret=secret
            ),
            "pseudonym_secret",
        ),
        (
            lambda: compute_anchor_hmac(state(), audit_hmac_secret=secret),
            "audit_hmac_secret",
        ),
        (
            lambda: verify_anchor_hmac(state(), ANCHOR_HMAC, audit_hmac_secret=secret),
            "audit_hmac_secret",
        ),
    ]:
        with pytest.raises(ValueError, match=field) as error:
            call()
        assert "private-marker" not in str(error.value)


class CustomInt(int):
    pass


class CustomStr(str):
    pass


class CustomBytes(bytes):
    pass


@pytest.mark.parametrize(
    "factory,field,value",
    [
        (bid, "v", 1),
        (bid, "sequence", 1),
        (bid, "amount_cents", 12000),
        (state, "v", 1),
        (state, "bid_count", 1),
    ],
)
def test_int_subclasses_are_rejected(factory, field, value):
    assert factory(**{field: value})
    with pytest.raises(ValueError, match=field):
        factory(**{field: CustomInt(value)})


@pytest.mark.parametrize(
    "factory,field,value",
    [
        (bid, "bidder_alias", ALIAS),
        (bid, "previous_hash", GENESIS_HASH),
        (state, "final_hash", BID_HASH),
        (lambda **kw: VerifiableBid(bid=bid(), **kw), "current_hash", BID_HASH),
    ],
)
def test_str_subclasses_are_rejected(factory, field, value):
    assert factory(**{field: value})
    with pytest.raises(ValueError, match=field):
        factory(**{field: CustomStr(value)})
    with pytest.raises(ValueError, match="signature"):
        verify_anchor_hmac(
            state(), CustomStr(ANCHOR_HMAC), audit_hmac_secret=AUDIT_SECRET
        )


def test_bytes_subclasses_are_rejected_as_secrets():
    with pytest.raises(ValueError, match="pseudonym_secret"):
        generate_bidder_alias(
            lot_id=LOT, user_id=USER, pseudonym_secret=CustomBytes(PSEUDONYM_SECRET)
        )
    with pytest.raises(ValueError, match="audit_hmac_secret"):
        compute_anchor_hmac(state(), audit_hmac_secret=CustomBytes(AUDIT_SECRET))
    with pytest.raises(ValueError, match="audit_hmac_secret"):
        verify_anchor_hmac(
            state(), ANCHOR_HMAC, audit_hmac_secret=CustomBytes(AUDIT_SECRET)
        )


def test_one_byte_secret_and_private_errors():
    assert re.fullmatch(
        r"Licitante-[0-9A-F]{16}",
        generate_bidder_alias(lot_id=LOT, user_id=USER, pseudonym_secret=b"x"),
    )
    signature = compute_anchor_hmac(state(), audit_hmac_secret=b"x")
    assert verify_anchor_hmac(state(), signature, audit_hmac_secret=b"x") is True
    with pytest.raises(ValueError) as error:
        bid(bidder_alias="private-marker")
    assert "private-marker" not in str(error.value)


@pytest.mark.parametrize("value", [{}, SimpleNamespace(), None])
def test_foreign_objects(value):
    for call in [
        lambda: canonical_bid_bytes(value),
        lambda: compute_bid_hash(value),
        lambda: canonical_anchor_bytes(value),
        lambda: compute_anchor_hmac(value, audit_hmac_secret=AUDIT_SECRET),
        lambda: verify_anchor_hmac(value, ANCHOR_HMAC, audit_hmac_secret=AUDIT_SECRET),
        lambda: VerifiableBid(bid=value, current_hash=BID_HASH),
    ]:
        with pytest.raises(ValueError):
            call()


@pytest.mark.parametrize("value", [str(LOT), 1, None])
def test_loose_uuid_arguments(value):
    for call in [
        lambda: generate_bidder_alias(
            lot_id=value, user_id=USER, pseudonym_secret=PSEUDONYM_SECRET
        ),
        lambda: generate_bidder_alias(
            lot_id=LOT, user_id=value, pseudonym_secret=PSEUDONYM_SECRET
        ),
        lambda: verify_bid_chain((), lot_id=value),
    ]:
        with pytest.raises(ValueError):
            call()


def test_pseudonym_golden(monkeypatch):
    original = integrity.hmac.new
    calls = []

    def spy(key, message, digestmod):
        result = original(key, message, digestmod)
        calls.append((key, message, digestmod, result.hexdigest()))
        return result

    monkeypatch.setattr(integrity.hmac, "new", spy)
    assert (
        generate_bidder_alias(
            lot_id=LOT, user_id=USER, pseudonym_secret=PSEUDONYM_SECRET
        )
        == ALIAS
    )
    assert calls == [
        (
            PSEUDONYM_SECRET,
            b"12345678-1234-5678-9abc-def012345678:87654321-4321-8765-abcd-0123456789ab",
            hashlib.sha256,
            "9374e0069a540cec1acdb860953a4af2edf74d9329b6a29b7537e3373ccaa8ba",
        )
    ]


def test_pseudonym_determinism_and_selected_changes():
    for _ in range(2):
        assert (
            generate_bidder_alias(
                lot_id=UUID(str(LOT).upper()),
                user_id=UUID(str(USER)),
                pseudonym_secret=PSEUDONYM_SECRET,
            )
            == ALIAS
        )
    for lot_id, user_id, secret in [
        (OTHER_LOT, USER, PSEUDONYM_SECRET),
        (LOT, UUID("87654321-4321-8765-abcd-0123456789ac"), PSEUDONYM_SECRET),
        (LOT, USER, b"atrio-test-pseudonym-v2"),
    ]:
        assert (
            generate_bidder_alias(
                lot_id=lot_id, user_id=user_id, pseudonym_secret=secret
            )
            != ALIAS
        )
    assert len(ALIAS) == 26
    assert str(USER) not in ALIAS and str(LOT) not in ALIAS
    assert set(inspect.signature(generate_bidder_alias).parameters) == {
        "lot_id",
        "user_id",
        "pseudonym_secret",
    }


def test_golden_bytes_and_digests():
    for _ in range(2):
        assert canonical_bid_bytes(bid()) == BID_BYTES
        assert compute_bid_hash(bid()) == BID_HASH
        assert canonical_anchor_bytes(state()) == ANCHOR_BYTES
        assert (
            compute_anchor_hmac(state(), audit_hmac_secret=AUDIT_SECRET) == ANCHOR_HMAC
        )
        empty = state(bid_count=0, final_hash=GENESIS_HASH)
        assert canonical_anchor_bytes(empty) == EMPTY_BYTES
        assert compute_anchor_hmac(empty, audit_hmac_secret=AUDIT_SECRET) == EMPTY_HMAC
    assert (
        GENESIS_HASH
        == "0000000000000000000000000000000000000000000000000000000000000000"
    )
    assert re.fullmatch("[0-9a-f]{64}", BID_HASH)
    reversed_fields = dict(
        reversed(
            [(f.name, getattr(bid(), f.name)) for f in dataclasses.fields(CanonicalBid)]
        )
    )
    assert canonical_bid_bytes(CanonicalBid(**reversed_fields)) == BID_BYTES


def test_serializer_options(monkeypatch):
    original = integrity.json.dumps
    options = []

    def spy(payload, **kwargs):
        options.append(kwargs)
        return original(payload, **kwargs)

    monkeypatch.setattr(integrity.json, "dumps", spy)
    for raw in [canonical_bid_bytes(bid()), canonical_anchor_bytes(state())]:
        assert isinstance(raw, bytes)
        assert not raw.endswith(b"\n") and not raw.startswith(b"\xef\xbb\xbf")
        obj = json.loads(raw)
        assert list(obj) == sorted(obj)
        assert type(obj["v"]) is int
        assert obj["lot_id"] == str(LOT)
    assert (
        options == [dict(sort_keys=True, separators=(",", ":"), ensure_ascii=False)] * 2
    )


class FoldOffset(tzinfo):
    def utcoffset(self, dt):
        return timedelta(hours=-3 if dt.fold == 0 else -4)

    def dst(self, dt):
        return timedelta(0)


class MissingOffset(tzinfo):
    def utcoffset(self, dt):
        return None


class InvalidOffset(tzinfo):
    def utcoffset(self, dt):
        return timedelta(days=2)


class WrongOffset(tzinfo):
    def utcoffset(self, dt):
        return "invalid"


@pytest.mark.parametrize(
    "value",
    [
        datetime(2026, 10, 23),
        date(2026, 10, 23),
        "2026-10-23",
        None,
        datetime(2026, 10, 23, tzinfo=MissingOffset()),
        datetime(2026, 10, 23, tzinfo=InvalidOffset()),
        datetime(2026, 10, 23, tzinfo=WrongOffset()),
        datetime.min.replace(tzinfo=timezone(timedelta(hours=1))),
        datetime.max.replace(tzinfo=timezone(timedelta(hours=-1))),
    ],
)
def test_timestamp_rejects_invalid(value):
    with pytest.raises(ValueError, match="timestamp"):
        bid(timestamp=value)


def test_timestamp_same_instant_and_day_change():
    local = datetime(
        2026, 10, 23, 1, 15, 30, 123456, tzinfo=timezone(timedelta(hours=-3))
    )
    assert canonical_bid_bytes(bid(timestamp=local)) == BID_BYTES
    assert bid(timestamp=local).timestamp == NOW
    assert bid(timestamp=local).timestamp.tzinfo is UTC
    india = datetime(
        2026, 10, 23, 0, 15, 30, 123456, tzinfo=timezone(timedelta(hours=5, minutes=30))
    )
    assert b"2026-10-22T18:45:30.123456Z" in canonical_bid_bytes(bid(timestamp=india))


@pytest.mark.parametrize("micros", [0, 1, 123456, 999999])
def test_timestamp_microseconds(micros):
    raw = canonical_bid_bytes(bid(timestamp=NOW.replace(microsecond=micros)))
    assert f".{micros:06d}Z".encode() in raw
    assert b"+00:00" not in raw


def test_timestamp_fold_and_extremes():
    first = bid(timestamp=datetime(2026, 11, 1, 1, 30, fold=0, tzinfo=FoldOffset()))
    second = bid(timestamp=datetime(2026, 11, 1, 1, 30, fold=1, tzinfo=FoldOffset()))
    assert b"04:30:00.000000Z" in canonical_bid_bytes(first)
    assert b"05:30:00.000000Z" in canonical_bid_bytes(second)
    assert compute_bid_hash(first) != compute_bid_hash(second)
    for value, expected in [
        (datetime.min.replace(tzinfo=UTC), b"0001-01-01T00:00:00.000000Z"),
        (datetime.max.replace(tzinfo=UTC), b"9999-12-31T23:59:59.999999Z"),
        (
            datetime(1, 1, 1, 1, tzinfo=timezone(timedelta(hours=1))),
            b"0001-01-01T00:00:00.000000Z",
        ),
        (
            datetime(
                9999, 12, 31, 22, 59, 59, 999999, tzinfo=timezone(timedelta(hours=-1))
            ),
            b"9999-12-31T23:59:59.999999Z",
        ),
    ]:
        assert expected in canonical_bid_bytes(bid(timestamp=value))


@pytest.mark.parametrize(
    "changes",
    [
        dict(amount_cents=12001),
        dict(bidder_alias="Licitante-AAAAAAAAAAAAAAAA"),
        dict(timestamp=NOW + timedelta(microseconds=1)),
        dict(previous_hash="a" * 64),
        dict(sequence=2),
        dict(lot_id=OTHER_LOT),
    ],
)
def test_hash_changes_with_each_field(changes):
    assert compute_bid_hash(bid(**changes)) != BID_HASH


def test_anchor_changes_with_each_input():
    for changes in [
        dict(lot_id=OTHER_LOT),
        dict(bid_count=2),
        dict(final_hash="a" * 64),
    ]:
        assert (
            compute_anchor_hmac(state(**changes), audit_hmac_secret=AUDIT_SECRET)
            != ANCHOR_HMAC
        )
    assert (
        compute_anchor_hmac(state(), audit_hmac_secret=b"atrio-test-audit-v2")
        != ANCHOR_HMAC
    )


def test_verify_uses_compare_digest(monkeypatch):
    original = integrity.hmac.compare_digest
    calls = []

    def spy(expected, signature):
        calls.append((expected, signature))
        return original(expected, signature)

    monkeypatch.setattr(integrity.hmac, "compare_digest", spy)
    assert (
        verify_anchor_hmac(state(), ANCHOR_HMAC, audit_hmac_secret=AUDIT_SECRET) is True
    )
    assert (
        verify_anchor_hmac(state(), "a" * 64, audit_hmac_secret=AUDIT_SECRET) is False
    )
    assert verify_anchor_hmac(state(), ANCHOR_HMAC, audit_hmac_secret=b"wrong") is False
    assert len(calls) == 3
    assert all(re.fullmatch("[0-9a-f]{64}", s) for pair in calls for s in pair)
    for call in [
        lambda: verify_anchor_hmac({}, ANCHOR_HMAC, audit_hmac_secret=AUDIT_SECRET),
        lambda: verify_anchor_hmac(state(), "", audit_hmac_secret=AUDIT_SECRET),
        lambda: verify_anchor_hmac(state(), ANCHOR_HMAC, audit_hmac_secret=b""),
    ]:
        with pytest.raises(ValueError):
            call()
    assert len(calls) == 3


@pytest.mark.parametrize("count", [0, 1, 2, 3])
def test_valid_chains(count, monkeypatch):
    records = chain(count)
    before = repr(records)

    def forbidden(**kwargs):
        pytest.fail("audit must use the historical alias")

    monkeypatch.setattr(integrity, "generate_bidder_alias", forbidden)
    for _ in range(2):
        assert verify_bid_chain(records, lot_id=UUID(str(LOT))) is True
    assert repr(records) == before


def record_changed(record, **changes):
    changed = dataclasses.replace(record.bid, **changes)
    return VerifiableBid(bid=changed, current_hash=compute_bid_hash(changed))


def test_chain_mismatches():
    records = chain()
    bad = [
        (record_changed(records[0], sequence=2),),
        (records[0], record_changed(records[1], sequence=3)),
        (records[0], record_changed(records[1], sequence=1)),
        (record_changed(records[0], previous_hash="a" * 64),),
        (records[0], record_changed(records[1], previous_hash="a" * 64)),
        (dataclasses.replace(records[0], current_hash="a" * 64),),
        tuple(reversed(records)),
        (records[0], records[0], *records[1:]),
        (records[0], records[2]),
        (record_changed(records[0], lot_id=OTHER_LOT),),
    ]
    for field in [
        dict(amount_cents=13000),
        dict(bidder_alias="Licitante-AAAAAAAAAAAAAAAA"),
        dict(timestamp=NOW + timedelta(microseconds=1)),
    ]:
        bad.append(
            (
                dataclasses.replace(
                    records[0], bid=dataclasses.replace(records[0].bid, **field)
                ),
            )
        )
    for altered in bad:
        assert verify_bid_chain(altered, lot_id=LOT) is False
    assert verify_bid_chain(records, lot_id=OTHER_LOT) is False
    for invalid in [[], {}, iter(records), "", None]:
        with pytest.raises(ValueError, match="records"):
            verify_bid_chain(invalid, lot_id=LOT)
    with pytest.raises(ValueError, match="records"):
        verify_bid_chain((bad[0][0], None), lot_id=LOT)


def rehashed(records):
    result = []
    previous = GENESIS_HASH
    for i, record in enumerate(records):
        changed = record_changed(
            record,
            previous_hash=previous,
            amount_cents=13000 if i == 0 else record.bid.amount_cents,
        )
        result.append(changed)
        previous = changed.current_hash
    return tuple(result)


@pytest.mark.parametrize(
    "attack",
    [
        "rehashed",
        "count",
        "final_hash",
        "old_summary",
        "truncated",
        "truncated_summary",
        "empty_nonempty",
        "last_rehashed",
    ],
)
def test_untrusted_previous_state_blocks_extension(attack):
    records = chain()
    previous = summary(records)
    signature = compute_anchor_hmac(previous, audit_hmac_secret=AUDIT_SECRET)
    if attack in {"rehashed", "old_summary"}:
        records = rehashed(records)
        if attack == "rehashed":
            previous = summary(records)
    elif attack == "last_rehashed":
        records = (*records[:-1], record_changed(records[-1], amount_cents=13000))
    elif attack == "count":
        previous = dataclasses.replace(previous, bid_count=4)
    elif attack == "final_hash":
        previous = dataclasses.replace(previous, final_hash="a" * 64)
    elif attack in {"truncated", "truncated_summary"}:
        records = records[:2]
        if attack == "truncated_summary":
            previous = summary(records)
    else:
        records = ()
    assert verify_bid_chain(records, lot_id=LOT) is True
    assert verify_anchor_hmac(previous, signature, audit_hmac_secret=AUDIT_SECRET) is (
        attack in {"old_summary", "truncated", "empty_nonempty", "last_rehashed"}
    )
    before = repr((records, previous, signature))
    emitted = []
    assert extend(records, previous, signature, emitted) is False
    assert emitted == []
    assert repr((records, previous, signature)) == before


@pytest.mark.parametrize("count", [0, 3])
def test_authenticated_previous_state_allows_extension(count):
    records = chain(count)
    previous = dataclasses.replace(summary(records), lot_id=UUID(str(LOT)))
    assert previous.lot_id is not LOT and previous.lot_id == LOT
    signature = compute_anchor_hmac(previous, audit_hmac_secret=AUDIT_SECRET)
    emitted = []
    assert extend(records, previous, signature, emitted) is True
    assert len(emitted) == 1
    new_records, new_state, new_signature = emitted[0]
    assert new_records[-1].bid.sequence == count + 1
    assert new_records[-1].bid.previous_hash == previous.final_hash
    assert authenticated(new_records, new_state, new_signature) is True
    # Restaurar conjunto antigo íntegro é rollback integral fora da garantia.
    assert authenticated(records, previous, signature) is True


def test_empty_anchor_from_another_lot_blocks_extension():
    previous = summary((), OTHER_LOT)
    signature = compute_anchor_hmac(previous, audit_hmac_secret=AUDIT_SECRET)
    assert verify_bid_chain((), lot_id=LOT) is True
    assert (
        verify_anchor_hmac(previous, signature, audit_hmac_secret=AUDIT_SECRET) is True
    )
    emitted = []
    assert extend((), previous, signature, emitted) is False
    assert emitted == []


@pytest.mark.parametrize("signature", [None, ""])
def test_missing_signature_never_bootstraps_extension(signature):
    emitted = []
    with pytest.raises(ValueError, match="signature"):
        extend((), summary(()), signature, emitted)
    assert emitted == []


def test_composition_does_not_hide_invalid_signature_after_chain_mismatch():
    with pytest.raises(ValueError, match="signature"):
        authenticated((record_changed(chain()[0], sequence=2),), summary(chain()), None)
