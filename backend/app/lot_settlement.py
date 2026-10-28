"""Internal atomic settlement and immutable receipt records (Story 4.3).

The command owns its Session and confirms once. Readers never settle or repair.
"""

import uuid
from collections.abc import Callable
from dataclasses import dataclass, fields
from datetime import datetime
from enum import StrEnum

from sqlalchemy import (
    BigInteger,
    CheckConstraint,
    DateTime,
    ForeignKey,
    ForeignKeyConstraint,
    Text,
    UniqueConstraint,
    select,
)
from sqlalchemy.orm import Mapped, Session, mapped_column

from app.bid_integrity import GENESIS_HASH, AnchorState, verify_anchor_hmac
from app.bids import (
    IntegrityConflict,
    IntegrityFailure,
    authenticate_previous_state,
    read_history,
)
from app.config import IntegrityConfig
from app.db import Base
from app.lots import Lot, database_now, lock_lot
from app.money import MAX_CENTS
from app.wallet import lock_wallet


class LotSettlement(Base):
    __tablename__ = "lot_settlements"
    __table_args__ = (
        UniqueConstraint("lot_id"),
        UniqueConstraint("id", "lot_id", name="uq_lot_settlements_id_lot_id"),
        ForeignKeyConstraint(
            ["lot_id", "winning_bid_sequence"],
            ["bids.lot_id", "bids.sequence"],
            ondelete="RESTRICT",
        ),
        CheckConstraint("outcome IN ('sold', 'unsold')", name="outcome_valid"),
        CheckConstraint("bid_count >= 0", name="bid_count_nonnegative"),
        CheckConstraint("final_hash ~ '^[0-9a-f]{64}$'", name="final_hash_format"),
        CheckConstraint("anchor_hmac ~ '^[0-9a-f]{64}$'", name="anchor_hmac_format"),
        CheckConstraint(
            "(outcome = 'sold' AND winner_user_id IS NOT NULL "
            "AND winner_alias IS NOT NULL "
            "AND winning_bid_sequence IS NOT NULL AND final_amount_cents IS NOT NULL "
            "AND bid_count > 0 AND winning_bid_sequence = bid_count "
            f"AND final_amount_cents > 0 AND final_amount_cents <= {MAX_CENTS} "
            "AND winner_alias ~ '^Licitante-[0-9A-F]{16}$') OR "
            "(outcome = 'unsold' AND winner_user_id IS NULL AND winner_alias IS NULL "
            "AND winning_bid_sequence IS NULL AND final_amount_cents IS NULL "
            f"AND bid_count = 0 AND final_hash = '{GENESIS_HASH}')",
            name="outcome_fields",
        ),
    )
    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    lot_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("lots.id", ondelete="RESTRICT")
    )
    outcome: Mapped[str] = mapped_column(Text)
    winner_user_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT")
    )
    winner_alias: Mapped[str | None] = mapped_column(Text)
    winning_bid_sequence: Mapped[int | None] = mapped_column(BigInteger)
    final_amount_cents: Mapped[int | None] = mapped_column(BigInteger)
    bid_count: Mapped[int] = mapped_column(BigInteger)
    final_hash: Mapped[str] = mapped_column(Text)
    anchor_hmac: Mapped[str] = mapped_column(Text)
    settled_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class Receipt(Base):
    __tablename__ = "receipts"
    __table_args__ = (
        UniqueConstraint("lot_id"),
        UniqueConstraint("settlement_id"),
        ForeignKeyConstraint(
            ["settlement_id", "lot_id"],
            ["lot_settlements.id", "lot_settlements.lot_id"],
            ondelete="RESTRICT",
        ),
        ForeignKeyConstraint(
            ["lot_id", "winning_bid_sequence"],
            ["bids.lot_id", "bids.sequence"],
            ondelete="RESTRICT",
        ),
        CheckConstraint(
            "bid_count > 0 AND winning_bid_sequence = bid_count",
            name="winning_bid_count",
        ),
        CheckConstraint(
            f"final_amount_cents > 0 AND final_amount_cents <= {MAX_CENTS}",
            name="amount_range",
        ),
        CheckConstraint(
            "winner_alias ~ '^Licitante-[0-9A-F]{16}$'", name="winner_alias_format"
        ),
        CheckConstraint("final_hash ~ '^[0-9a-f]{64}$'", name="final_hash_format"),
    )
    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    lot_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("lots.id", ondelete="RESTRICT")
    )
    settlement_id: Mapped[uuid.UUID] = mapped_column()
    winning_bid_sequence: Mapped[int] = mapped_column(BigInteger)
    winner_alias: Mapped[str] = mapped_column(Text)
    final_amount_cents: Mapped[int] = mapped_column(BigInteger)
    settled_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    bid_count: Mapped[int] = mapped_column(BigInteger)
    final_hash: Mapped[str] = mapped_column(Text)


@dataclass(frozen=True)
class SettlementRecord:
    id: uuid.UUID
    lot_id: uuid.UUID
    outcome: str
    winner_user_id: uuid.UUID | None
    winner_alias: str | None
    winning_bid_sequence: int | None
    final_amount_cents: int | None
    bid_count: int
    final_hash: str
    anchor_hmac: str
    settled_at: datetime


@dataclass(frozen=True)
class ReceiptRecord:
    id: uuid.UUID
    lot_id: uuid.UUID
    settlement_id: uuid.UUID
    winning_bid_sequence: int
    winner_alias: str
    final_amount_cents: int
    settled_at: datetime
    bid_count: int
    final_hash: str


class SettlementStatus(StrEnum):
    SETTLED_SOLD = "settled_sold"
    SETTLED_UNSOLD = "settled_unsold"
    ALREADY_SETTLED = "already_settled"
    NOT_DUE = "not_due"


class SettlementRefusal(StrEnum):
    LOT_CANCELLED = "lot_cancelled"


class SettlementFinancialFailure(StrEnum):
    CREDIT_LIMIT_EXCEEDED = "credit_limit_exceeded"
    INSUFFICIENT_COMMITMENT = "insufficient_commitment"
    WALLET_INVARIANT_CONFLICT = "wallet_invariant_conflict"


class SettlementFinancialConflict(RuntimeError):
    def __init__(self, reason: SettlementFinancialFailure):
        self.reason = reason
        super().__init__(reason.value)


@dataclass(frozen=True)
class PreparedSettlement:
    status: SettlementStatus
    lot_id: uuid.UUID
    settlement: SettlementRecord | None
    receipt: ReceiptRecord | None


@dataclass(frozen=True)
class SettlementResult:
    status: SettlementStatus
    lot_id: uuid.UUID
    settlement: SettlementRecord | None
    receipt: ReceiptRecord | None
    transitioned: bool


def _record(record_type, source):
    return record_type(
        **{field.name: getattr(source, field.name) for field in fields(record_type)}
    )


def _read_pair(session: Session, lot_id: uuid.UUID):
    # One statement: receipt absence and all copied fields share the same snapshot.
    settlement_columns = [
        getattr(LotSettlement, f.name).label("s_" + f.name)
        for f in fields(SettlementRecord)
    ]
    receipt_columns = [
        getattr(Receipt, f.name).label("r_" + f.name) for f in fields(ReceiptRecord)
    ]
    row = session.execute(
        select(*settlement_columns, *receipt_columns)
        .select_from(Lot)
        .outerjoin(LotSettlement, LotSettlement.lot_id == Lot.id)
        .outerjoin(Receipt, Receipt.lot_id == Lot.id)
        .where(Lot.id == lot_id)
        .execution_options(autoflush=False)
    ).one_or_none()
    if row is None:
        return None, None
    data = row._mapping
    settlement = (
        SettlementRecord(
            **{f.name: data["s_" + f.name] for f in fields(SettlementRecord)}
        )
        if data["s_id"]
        else None
    )
    receipt = (
        ReceiptRecord(**{f.name: data["r_" + f.name] for f in fields(ReceiptRecord)})
        if data["r_id"]
        else None
    )
    return settlement, receipt


def _structural_conflict(settlement, receipt):
    if settlement is None:
        return IntegrityConflict(IntegrityFailure.RECEIPT_MISMATCH) if receipt else None
    if settlement.outcome == "unsold":
        if (
            receipt is not None
            or any(
                getattr(settlement, name) is not None
                for name in (
                    "winner_user_id",
                    "winner_alias",
                    "winning_bid_sequence",
                    "final_amount_cents",
                )
            )
            or settlement.bid_count != 0
            or settlement.final_hash != GENESIS_HASH
        ):
            return IntegrityConflict(IntegrityFailure.SETTLEMENT_MISMATCH)
    elif settlement.outcome == "sold":
        if receipt is None or receipt.settlement_id != settlement.id:
            return IntegrityConflict(IntegrityFailure.RECEIPT_MISMATCH)
        for name in (
            "lot_id",
            "winning_bid_sequence",
            "winner_alias",
            "final_amount_cents",
            "settled_at",
            "bid_count",
            "final_hash",
        ):
            if getattr(settlement, name) != getattr(receipt, name):
                return IntegrityConflict(IntegrityFailure.RECEIPT_MISMATCH)
    else:
        return IntegrityConflict(IntegrityFailure.SETTLEMENT_MISMATCH)
    return None


def read_settlement(
    session: Session, lot_id: uuid.UUID
) -> SettlementRecord | IntegrityConflict | None:
    settlement, receipt = _read_pair(session, lot_id)
    return _structural_conflict(settlement, receipt) or settlement


def read_receipt(
    session: Session, lot_id: uuid.UUID
) -> ReceiptRecord | IntegrityConflict | None:
    settlement, receipt = _read_pair(session, lot_id)
    return _structural_conflict(settlement, receipt) or receipt


def prepare_settlement(
    session: Session, *, lot_id: uuid.UUID, integrity: IntegrityConfig
) -> PreparedSettlement | IntegrityConflict | SettlementRefusal | None:
    lot = lock_lot(session, lot_id)
    if lot is None:
        return None
    now = database_now(session)
    settlement, receipt = _read_pair(session, lot_id)
    conflict = _structural_conflict(settlement, receipt)
    if conflict:
        return conflict
    if lot.cancelled_at is not None:
        return (
            IntegrityConflict(IntegrityFailure.SETTLEMENT_MISMATCH)
            if settlement
            else SettlementRefusal.LOT_CANCELLED
        )
    if settlement is None and now < lot.ends_at:
        return PreparedSettlement(SettlementStatus.NOT_DUE, lot_id, None, None)
    rows = read_history(session, lot_id)
    authenticated = authenticate_previous_state(
        lot, rows, integrity=integrity, lot_id=lot_id
    )
    if isinstance(authenticated, IntegrityConflict):
        return authenticated
    if settlement is not None:
        if (
            settlement.settled_at < lot.ends_at
            or settlement.bid_count != authenticated.bid_count
            or settlement.final_hash != authenticated.final_hash
            or settlement.anchor_hmac != lot.anchor_hmac
        ):
            return IntegrityConflict(IntegrityFailure.SETTLEMENT_MISMATCH)
        if not verify_anchor_hmac(
            AnchorState(
                v=1,
                lot_id=lot_id,
                bid_count=settlement.bid_count,
                final_hash=settlement.final_hash,
            ),
            settlement.anchor_hmac,
            audit_hmac_secret=integrity.audit_hmac_secret,
        ):
            return IntegrityConflict(IntegrityFailure.SETTLEMENT_MISMATCH)
        if rows:
            last = rows[-1]
            if (
                settlement.outcome != "sold"
                or settlement.winner_user_id != last.bidder_id
                or settlement.winner_alias != last.bidder_alias
                or settlement.final_amount_cents != last.amount_cents
                or settlement.winning_bid_sequence != last.sequence
                or settlement.winner_user_id == lot.auctioneer_id
            ):
                return IntegrityConflict(IntegrityFailure.SETTLEMENT_MISMATCH)
        elif settlement.outcome != "unsold":
            return IntegrityConflict(IntegrityFailure.SETTLEMENT_MISMATCH)
        return PreparedSettlement(
            SettlementStatus.ALREADY_SETTLED, lot_id, settlement, receipt
        )
    last = rows[-1] if rows else None
    if last is not None:
        if last.bidder_id == lot.auctioneer_id:
            return IntegrityConflict(IntegrityFailure.OPERATIONAL_MISMATCH)
        wallets = {
            user_id: lock_wallet(session, user_id)
            for user_id in sorted({last.bidder_id, lot.auctioneer_id})
        }
        winner, seller = wallets[last.bidder_id], wallets[lot.auctioneer_id]
        for wallet in (winner, seller):
            if (
                not 0
                <= wallet.committed_balance_cents
                <= wallet.total_balance_cents
                <= MAX_CENTS
            ):
                raise SettlementFinancialConflict(
                    SettlementFinancialFailure.WALLET_INVARIANT_CONFLICT
                )
        amount = last.amount_cents
        if winner.committed_balance_cents < amount:
            raise SettlementFinancialConflict(
                SettlementFinancialFailure.INSUFFICIENT_COMMITMENT
            )
        if seller.total_balance_cents + amount > MAX_CENTS:
            raise SettlementFinancialConflict(
                SettlementFinancialFailure.CREDIT_LIMIT_EXCEEDED
            )
        # Both columns in ONE update: immediate C <= T CHECK must always hold.
        winner.total_balance_cents -= amount
        winner.committed_balance_cents -= amount
        session.flush()
        seller.total_balance_cents += amount
        session.flush()
    model = LotSettlement(
        id=uuid.uuid4(),
        lot_id=lot_id,
        outcome="sold" if last else "unsold",
        winner_user_id=last.bidder_id if last else None,
        winner_alias=last.bidder_alias if last else None,
        winning_bid_sequence=last.sequence if last else None,
        final_amount_cents=last.amount_cents if last else None,
        bid_count=authenticated.bid_count,
        final_hash=authenticated.final_hash,
        anchor_hmac=lot.anchor_hmac,
        settled_at=now,
    )
    session.add(model)
    session.flush()
    settlement = _record(SettlementRecord, model)
    receipt = None
    if last:
        receipt_model = Receipt(
            id=uuid.uuid4(),
            settlement_id=model.id,
            **{
                name: getattr(model, name)
                for name in (
                    "lot_id",
                    "winning_bid_sequence",
                    "winner_alias",
                    "final_amount_cents",
                    "settled_at",
                    "bid_count",
                    "final_hash",
                )
            },
        )
        session.add(receipt_model)
        session.flush()
        receipt = _record(ReceiptRecord, receipt_model)
    return PreparedSettlement(
        SettlementStatus.SETTLED_SOLD if last else SettlementStatus.SETTLED_UNSOLD,
        lot_id,
        settlement,
        receipt,
    )


def settle_lot(
    session_factory: Callable[[], Session],
    *,
    lot_id: uuid.UUID,
    integrity: IntegrityConfig,
) -> SettlementResult | IntegrityConflict | SettlementRefusal | None:
    with session_factory() as session:
        try:
            prepared = prepare_settlement(session, lot_id=lot_id, integrity=integrity)
            if not isinstance(prepared, PreparedSettlement):
                session.rollback()
                return prepared
            transitioned = prepared.status in (
                SettlementStatus.SETTLED_SOLD,
                SettlementStatus.SETTLED_UNSOLD,
            )
            if transitioned:
                session.commit()
            else:
                session.rollback()
            # Only the confirmed command can expose transitioned.
            return SettlementResult(
                prepared.status,
                lot_id,
                prepared.settlement,
                prepared.receipt,
                transitioned,
            )
        except Exception:
            session.rollback()
            raise
