"""Database model for revoked JWT tokens (Token Blocklist)."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, select
from sqlalchemy.orm import Mapped, mapped_column

from app.extensions import db
from app.models.base import CRUDMixin, utc_now


class TokenBlocklist(CRUDMixin, db.Model):
    """Stores revoked JWT token identifiers (JTI) to enforce immediate logout and token rotation."""

    __tablename__ = "token_blocklist"

    jti: Mapped[str] = mapped_column(
        String(64), unique=True, index=True, nullable=False
    )
    token_type: Mapped[str] = mapped_column(String(20), nullable=False)
    user_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        index=True,
        nullable=True,
    )
    revoked_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, nullable=False
    )

    @classmethod
    def is_jti_blocked(cls, jti: str) -> bool:
        """Check whether a JWT token identifier (JTI) has been revoked."""
        stmt = select(cls.id).where(cls.jti == jti)
        return db.session.scalar(stmt) is not None

    @classmethod
    def revoke_token(
        cls, jti: str, token_type: str, user_id: int | None = None
    ) -> TokenBlocklist:
        """Persist a revoked token JTI in the blocklist if not already present."""
        existing = db.session.scalar(select(cls).where(cls.jti == jti))
        if existing is not None:
            return existing
        entry = cls(jti=jti, token_type=token_type, user_id=user_id)
        return entry.save()
