"""Fase temporal do lote, regra pura (AD-6, AD-26; Story 3.2 P8).

Só biblioteca padrão: não importa FastAPI, SQLAlchemy, catálogo nem ORM, e nunca lê
relógio. O `now` é sempre entrada. As comparações são entre instantes: cada argumento é
normalizado para UTC, então o offset (e o `fold` de uma hora repetida) não muda o
resultado.
"""

from datetime import UTC, datetime
from enum import StrEnum


class LotPhase(StrEnum):
    """Fase temporal do lote (2.4 §7, Story 2.5 P2). Derivada, nunca persistida: fim
    temporal não é liquidação, que só nasce na 4.3 (P8)."""

    SCHEDULED = "scheduled"
    LIVE = "live"
    ENDED = "ended"


def require_aware(name: str, value: object) -> datetime:
    """Erro de programação se `value` não for um instante com fuso."""
    if not isinstance(value, datetime):
        raise ValueError(f"{name} must be a datetime")
    if value.utcoffset() is None:
        raise ValueError(f"{name} must be timezone-aware")
    return value


def check_lot_window(starts_at: datetime, ends_at: datetime) -> None:
    """Erro de programação se a janela do lote não for um intervalo crescente de
    instantes com fuso."""
    require_aware("starts_at", starts_at)
    require_aware("ends_at", ends_at)
    if starts_at.astimezone(UTC) >= ends_at.astimezone(UTC):
        raise ValueError("starts_at must be before ends_at")


def lot_phase(starts_at: datetime, ends_at: datetime, now: datetime) -> LotPhase:
    """`now < starts_at` agendado; `starts_at <= now < ends_at` ao vivo; `now >=
    ends_at` encerrado. Compara instantes: o offset de cada argumento não importa."""
    check_lot_window(starts_at, ends_at)
    now_utc = require_aware("now", now).astimezone(UTC)
    if now_utc < starts_at.astimezone(UTC):
        return LotPhase.SCHEDULED
    if now_utc < ends_at.astimezone(UTC):
        return LotPhase.LIVE
    return LotPhase.ENDED
