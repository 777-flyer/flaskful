"""Sample Item database model with public UUID, soft deletion, and user ownership."""

from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.extensions import db
from app.models.base import CRUDMixin, SoftDeleteMixin, TimestampMixin, UUIDMixin

if TYPE_CHECKING:
    from app.models.user import User


class Item(CRUDMixin, UUIDMixin, TimestampMixin, SoftDeleteMixin, db.Model):
    """Sample Item resource owned by a User with soft-delete support."""

    __tablename__ = "items"

    title: Mapped[str] = mapped_column(String(150), index=True, nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(
        String(30), default="active", index=True, nullable=False
    )
    owner_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )

    owner: Mapped[User] = relationship("User", back_populates="items")

    def __repr__(self) -> str:
        return f"<Item id={self.id} uuid={self.uuid!r} title={self.title!r}>"
