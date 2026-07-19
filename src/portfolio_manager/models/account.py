"""Brokerage account model — user-scoped.

Represents a brokerage account (e.g., "Wacky", "Long-term Stable") at an institution.
"""


from datetime import UTC, datetime
from uuid import UUID, uuid4

from sqlalchemy import Column, DateTime, ForeignKey, func
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped
from sqlmodel import Field, Relationship, SQLModel


class Account(SQLModel, table=True):
    __tablename__ = "accounts"

    id: UUID = Field(default_factory=uuid4, sa_column=Column(PG_UUID(as_uuid=True), primary_key=True))
    user_id: UUID = Field(
        sa_column=Column(PG_UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True),
    )
    name: str = Field(max_length=100)
    institution: str | None = Field(default=None, max_length=100)
    account_number: str | None = Field(default=None, max_length=50)
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        sa_column=Column(DateTime(timezone=True), nullable=False, server_default=func.now()),
    )

    # Relationships
    user: User = Relationship(back_populates="accounts")
    portfolios: Mapped[list['Portfolio']] = Relationship(back_populates="account")


# ── Pydantic schemas (no table) ─────────────────────────────────────────


class AccountCreate(SQLModel):
    """Schema for creating a new account."""

    name: str = Field(max_length=100)
    institution: str | None = None
    account_number: str | None = None


class AccountUpdate(SQLModel):
    """Schema for updating an account."""

    name: str | None = None
    institution: str | None = None
    account_number: str | None = None


class AccountRead(SQLModel, table=False):
    """Schema for reading an account."""

    id: UUID
    user_id: UUID
    name: str
    institution: str | None = None
    account_number: str | None = None
    created_at: datetime
