"""User database model with scrypt password hashing, RBAC role, and brute-force lockout protection."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, DateTime, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship
from werkzeug.security import check_password_hash, generate_password_hash

from app.extensions import db
from app.models.base import CRUDMixin, TimestampMixin, utc_now

if TYPE_CHECKING:
    from app.models.item import Item

PASSWORD_HASH_METHOD = "scrypt:32768:8:1"
# Precomputed dummy hash used to mitigate timing-based user enumeration when email is not found
DUMMY_PASSWORD_HASH = generate_password_hash(
    "DummyTimingMitigationPass!99", method=PASSWORD_HASH_METHOD
)


class User(CRUDMixin, TimestampMixin, db.Model):
    """User account model with RBAC and brute-force lockout tracking."""

    __tablename__ = "users"

    username: Mapped[str] = mapped_column(
        String(80), unique=True, index=True, nullable=False
    )
    email: Mapped[str] = mapped_column(
        String(120), unique=True, index=True, nullable=False
    )
    password_hash: Mapped[str] = mapped_column(String(256), nullable=False)
    role: Mapped[str] = mapped_column(
        String(30), default="user", index=True, nullable=False
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    # Brute-force protection fields
    failed_login_attempts: Mapped[int] = mapped_column(
        Integer, default=0, nullable=False
    )
    locked_until: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    items: Mapped[list[Item]] = relationship(
        "Item",
        back_populates="owner",
        cascade="all, delete-orphan",
        lazy="selectin",
    )

    def set_password(self, raw_password: str) -> None:
        """Hash and store the user's password using memory-hard scrypt."""
        self.password_hash = generate_password_hash(
            raw_password, method=PASSWORD_HASH_METHOD
        )

    def check_password(self, raw_password: str) -> bool:
        """Verify a plaintext password against the stored hash."""
        return check_password_hash(self.password_hash, raw_password)

    @staticmethod
    def verify_dummy_password(raw_password: str) -> None:
        """Perform a constant-time dummy hash check to prevent email enumeration via timing."""
        check_password_hash(DUMMY_PASSWORD_HASH, raw_password)

    def is_locked(self) -> bool:
        """Return True if the account is currently locked due to failed login attempts."""
        if self.locked_until is None:
            return False
        locked_until_utc = (
            self.locked_until
            if self.locked_until.tzinfo is not None
            else self.locked_until.replace(tzinfo=UTC)
        )
        return utc_now() < locked_until_utc

    def record_failed_login(
        self, max_attempts: int = 5, lockout_minutes: int = 15
    ) -> None:
        """Increment failed login counter and lock the account if threshold is reached."""
        self.failed_login_attempts += 1
        if self.failed_login_attempts >= max_attempts:
            self.locked_until = utc_now() + timedelta(minutes=lockout_minutes)
        self.save()

    def reset_failed_logins(self) -> None:
        """Clear failed login counter and lockout timestamp after successful login."""
        if self.failed_login_attempts > 0 or self.locked_until is not None:
            self.failed_login_attempts = 0
            self.locked_until = None
            self.save()

    def __repr__(self) -> str:
        return f"<User id={self.id} username={self.username!r} role={self.role!r}>"
