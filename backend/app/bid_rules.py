"""Regra pura da aceitação do lance (Story 3.2; AD-5, AD-7, AD-26; P1 a P13, C1).

Precedência das recusas, contrato (P3, AD-7): período → mínimo → líder → saldo; o
anti-sniping só roda para lance aceito. A ordem é verificada por testes, não pela
leitura do código.

O fluxo da 3.4 em duas partes: `evaluate_pre_wallet` (período, mínimo, líder; antes de
travar carteiras, sem saldo) e `evaluate_post_wallet` (saldo e anti-sniping; depois das
travas). Para entradas estruturalmente válidas, `evaluate_bid` equivale à composição
das duas. Por D8, valida o saldo separado antes de qualquer recusa de negócio.

Não importa ORM, FastAPI, Pydantic, `Session` nem lê relógio: o `now` é sempre entrada.
Estado inválido é erro de programação (`ValueError`), nunca recusa de negócio.
"""

import uuid
from dataclasses import InitVar, dataclass
from datetime import UTC, datetime, timedelta
from enum import StrEnum

from app.lot_time import LotPhase, check_lot_window, lot_phase, require_aware
from app.money import MAX_CENTS

ANTI_SNIPING_WINDOW = timedelta(minutes=2)  # AD-5: 0 < restante <= janela
ANTI_SNIPING_RENEWAL = timedelta(minutes=2)  # AD-5: o fim alvo é `now` + renovação


class BidRefusal(StrEnum):
    """Motivo de recusa de negócio (P2). Código de domínio, fora de `errors.py`: o
    contrato HTTP e a mensagem nascem com o endpoint (3.4 e 3.5)."""

    # Declarados na ordem da precedência (P3); o código não usa a ordem dos membros.
    LOT_NOT_STARTED = "lot_not_started"
    LOT_ENDED = "lot_ended"
    BELOW_MINIMUM = "below_minimum"
    ALREADY_WINNING = "already_winning"
    INSUFFICIENT_BALANCE = "insufficient_balance"
    # Story 3.6, D4: não vem das regras puras. `place_bid` a devolve depois do gate,
    # para o lote cancelado, antes de qualquer regra de aceitação.
    LOT_CANCELLED = "lot_cancelled"


# --- validação por dono (P7, P10): cada invariante vive num só lugar ---


def _require_cents(name: str, value: object, lowest: int) -> int:
    # `bool` é subtipo de `int`: precisa ser recusado antes do isinstance(int).
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError(f"{name} must be integer cents")
    if not lowest <= value <= MAX_CENTS:
        raise ValueError(f"{name} out of range")
    return value


def _require_user_id(name: str, value: object) -> uuid.UUID:
    if not isinstance(value, uuid.UUID):
        raise ValueError(f"{name} must be a UUID")
    return value


# --- tipos de domínio (P1, P4, P5, C1, D6) ---


@dataclass(frozen=True, kw_only=True)
class CurrentBid:
    """Lance atual: valor e líder são inseparáveis (P4)."""

    amount_cents: int
    leader_id: uuid.UUID

    def __post_init__(self) -> None:
        _require_cents("amount_cents", self.amount_cents, 1)
        _require_user_id("leader_id", self.leader_id)


@dataclass(frozen=True, kw_only=True)
class LotBidState:
    """O que a regra precisa saber do lote, sem ORM. `current=None` é "sem lance"."""

    starts_at: datetime
    ends_at: datetime
    starting_bid_cents: int
    min_increment_cents: int
    current: CurrentBid | None

    def __post_init__(self) -> None:
        check_lot_window(self.starts_at, self.ends_at)
        _require_cents("starting_bid_cents", self.starting_bid_cents, 1)
        _require_cents("min_increment_cents", self.min_increment_cents, 1)
        if self.current is not None:
            if not isinstance(self.current, CurrentBid):
                raise ValueError("current must be a CurrentBid or None")
            if self.current.amount_cents < self.starting_bid_cents:
                raise ValueError("current bid below starting bid")


@dataclass(frozen=True, kw_only=True)
class BidAttempt:
    """Só a tentativa do licitante. O saldo é da carteira e entra à parte (C1)."""

    bidder_id: uuid.UUID
    amount_cents: int

    def __post_init__(self) -> None:
        _require_user_id("bidder_id", self.bidder_id)
        _require_cents("amount_cents", self.amount_cents, 1)


@dataclass(frozen=True, kw_only=True)
class BidAccepted:
    """Lance aceito. `ends_at` é o fim efetivo (UTC), sempre presente (P5)."""

    ends_at: datetime
    anti_sniping_applied: bool

    def __post_init__(self) -> None:
        require_aware("ends_at", self.ends_at)
        if not isinstance(self.anti_sniping_applied, bool):
            raise ValueError("anti_sniping_applied must be a bool")


_ISSUED_BY_PRE_WALLET = object()


@dataclass(frozen=True, kw_only=True)
class EligibleBid:
    """Tentativa que passou período, mínimo e líder. Só `evaluate_pre_wallet` a emite
    (D3): é como a etapa de saldo sabe que a pré-carteira rodou. Carrega só o que a
    etapa seguinte usa."""

    amount_cents: int
    ends_at: datetime  # UTC
    now: datetime  # UTC
    issued: InitVar[object] = None

    def __post_init__(self, issued: object) -> None:
        if issued is not _ISSUED_BY_PRE_WALLET:
            raise ValueError("EligibleBid is issued only by evaluate_pre_wallet")


# --- mínimo exigido (P5, P6) ---


def minimum_bid_cents(lot: LotBidState) -> int | None:
    """Próximo lance mínimo, ou None quando nenhum valor até MAX_CENTS o alcança."""
    if not isinstance(lot, LotBidState):
        raise ValueError("lot must be a LotBidState")
    if lot.current is None:
        return lot.starting_bid_cents
    # int exato do Python: não há overflow, só irrepresentabilidade (nunca clamp).
    minimum = lot.current.amount_cents + lot.min_increment_cents
    return minimum if minimum <= MAX_CENTS else None


# --- etapa pré-carteira: período → mínimo → líder (P3, P11, C1) ---


def evaluate_pre_wallet(
    lot: LotBidState, attempt: BidAttempt, now: datetime
) -> EligibleBid | BidRefusal:
    """Período → mínimo → líder, nesta ordem (P3, AD-7 passos 4 a 6). Sem saldo."""
    if not isinstance(lot, LotBidState):
        raise ValueError("lot must be a LotBidState")
    if not isinstance(attempt, BidAttempt):
        raise ValueError("attempt must be a BidAttempt")
    # 1. Período: a semântica única de lot_phase (também valida now).
    phase = lot_phase(lot.starts_at, lot.ends_at, now)
    if phase is LotPhase.SCHEDULED:
        return BidRefusal.LOT_NOT_STARTED
    if phase is LotPhase.ENDED:
        return BidRefusal.LOT_ENDED
    # 2. Mínimo: None = nenhum valor representável o alcança.
    minimum = minimum_bid_cents(lot)
    if minimum is None or attempt.amount_cents < minimum:
        return BidRefusal.BELOW_MINIMUM
    # 3. Líder não cobre o próprio lance.
    if lot.current is not None and attempt.bidder_id == lot.current.leader_id:
        return BidRefusal.ALREADY_WINNING
    return EligibleBid(
        amount_cents=attempt.amount_cents,
        ends_at=lot.ends_at.astimezone(UTC),
        now=now.astimezone(UTC),
        issued=_ISSUED_BY_PRE_WALLET,
    )


# --- etapa pós-carteira: saldo e anti-sniping (P3, P5, AD-5) ---


def evaluate_post_wallet(
    eligible: EligibleBid, available_balance_cents: int
) -> BidAccepted | BidRefusal:
    """Saldo e, só para lance aceito, o anti-sniping (AD-7 passos 9 e 13)."""
    if not isinstance(eligible, EligibleBid):
        raise ValueError("eligible must be an EligibleBid")
    _require_cents("available_balance_cents", available_balance_cents, 0)
    # 4. Saldo disponível (total − comprometido), da carteira travada pela 3.4.
    if eligible.amount_cents > available_balance_cents:
        return BidRefusal.INSUFFICIENT_BALANCE
    # 5. Aceito. Só agora o anti-sniping: 0 < restante <= janela (AD-5, inclusiva).
    # `ends_at` e `now` de `eligible` já estão em UTC: a subtração é entre instantes.
    remaining = eligible.ends_at - eligible.now
    if timedelta(0) < remaining <= ANTI_SNIPING_WINDOW:
        # Renovação (AD-5, revisada em 27/10/2026): o fim alvo é `now` + 2 min, com o
        # mesmo `now` lido sob a trava; cada lance na janela renova o prazo, sem teto.
        # Com exatamente 2 min restantes o alvo é o próprio `ends_at`: não há mudança
        # efetiva e `anti_sniping_applied` fica falso. O fim nunca diminui.
        target = eligible.now + ANTI_SNIPING_RENEWAL
        if target > eligible.ends_at:
            return BidAccepted(ends_at=target, anti_sniping_applied=True)
    return BidAccepted(ends_at=eligible.ends_at, anti_sniping_applied=False)


# --- avaliação completa (P1, C1, D2, D8) ---


def evaluate_bid(
    lot: LotBidState,
    attempt: BidAttempt,
    available_balance_cents: int,
    now: datetime,
) -> BidAccepted | BidRefusal:
    """Para entradas estruturalmente válidas, equivale à composição
    `evaluate_pre_wallet` → `evaluate_post_wallet` que a 3.4 executa em duas partes.
    Por D8, valida o saldo separado antecipadamente: saldo corrompido levanta
    `ValueError` antes de qualquer recusa de negócio, inclusive temporal.
    Precedência (contrato, P3): período → mínimo → líder → saldo;
    anti-sniping só no aceite.
    """
    # Saldo corrompido nunca se esconde atrás de uma recusa de período (P7, D8).
    _require_cents("available_balance_cents", available_balance_cents, 0)
    checked = evaluate_pre_wallet(lot, attempt, now)
    if isinstance(checked, BidRefusal):
        return checked
    return evaluate_post_wallet(checked, available_balance_cents)
