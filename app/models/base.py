"""Base mixins for SQLAlchemy 2.0 models."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Self

from sqlalchemy import DateTime
from sqlalchemy.orm import Mapped, mapped_column

from app.extensions import db


def utc_now() -> datetime:
    """Return current UTC datetime."""
    return datetime.now(timezone.utc)


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
        """Delete the instance from the session and optionally commit."""
        db.session.delete(self)
        if commit:
            db.session.commit()

