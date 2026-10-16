"""Base mixins for SQLAlchemy 2.0 models (Timestamps, Public UUIDs, Soft Deletes, and CRUD)."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Self

from sqlalchemy import DateTime, String
from sqlalchemy.orm import Mapped, mapped_column

from app.extensions import db


def utc_now() -> datetime:
    """Return current UTC datetime."""
    return datetime.now(UTC)


def generate_uuid() -> str:
    """Return a new UUIDv4 string."""
    return str(uuid.uuid4())


class UUIDMixin:
    """Mixin that adds an indexed, non-enumerable public UUIDv4 identifier."""

    uuid: Mapped[str] = mapped_column(
        String(36),
        default=generate_uuid,
        unique=True,
        index=True,
        nullable=False,
    )


class TimestampMixin:
    """Mixin that adds created_at and updated_at UTC timestamps to models."""

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utc_now,
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utc_now,
        onupdate=utc_now,
        nullable=False,
    )


class SoftDeleteMixin:
    """Mixin that supports soft deletion (archiving) and restoration of records."""

    deleted_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        default=None,
        index=True,
        nullable=True,
    )

    @property
    def is_deleted(self) -> bool:
        """Return True if the record has been soft-deleted."""
        return self.deleted_at is not None

    def soft_delete(self, commit: bool = True) -> Self:
        """Mark the record as deleted with the current UTC timestamp."""
        self.deleted_at = utc_now()
        db.session.add(self)
        if commit:
            db.session.commit()
        return self

    def restore(self, commit: bool = True) -> Self:
        """Restore a previously soft-deleted record."""
        self.deleted_at = None
        db.session.add(self)
        if commit:
            db.session.commit()
        return self


class CRUDMixin:
    """Mixin that adds convenience persistence helpers to SQLAlchemy models."""

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)

    def save(self, commit: bool = True) -> Self:
        """Add the instance to the session and optionally commit."""
        db.session.add(self)
        if commit:
            db.session.commit()
        return self

    def delete(self, commit: bool = True) -> None:
        """Permanently delete the instance from the database."""
        db.session.delete(self)
        if commit:
            db.session.commit()
