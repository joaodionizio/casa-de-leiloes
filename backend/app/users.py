"""Usuários e papéis (Story 2.2, AD-11, AD-30)."""

import uuid
from enum import StrEnum

from sqlalchemy import CheckConstraint, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


class UserRole(StrEnum):
    """Papéis técnicos em inglês; "Leiloeiro"/"Licitante" só na interface."""

    AUCTIONEER = "AUCTIONEER"
    BIDDER = "BIDDER"


class User(Base):
    """Espelha a migration `0002`; o esquema dos testes vem sempre dela."""

    __tablename__ = "users"
    __table_args__ = (
        CheckConstraint("email = lower(email)", name="email_lowercase"),
        CheckConstraint("role IN ('AUCTIONEER', 'BIDDER')", name="role"),
    )

    # Sem default no banco: os IDs do seed são fixos.
    id: Mapped[uuid.UUID] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(String(254), unique=True)
    password_hash: Mapped[str] = mapped_column(Text)
    role: Mapped[str] = mapped_column(String(16))
