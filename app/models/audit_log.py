"""Security and operational AuditLog database model."""

from __future__ import annotations

from datetime import datetime

from flask import g, has_request_context, request
from sqlalchemy import DateTime, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from app.extensions import db
from app.models.base import CRUDMixin, utc_now


class AuditLog(CRUDMixin, db.Model):
    """Immutable security and operational audit trail entry."""

    __tablename__ = "audit_logs"

    user_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"),
        index=True,
        nullable=True,
    )
    action: Mapped[str] = mapped_column(String(64), index=True, nullable=False)
    resource_type: Mapped[str | None] = mapped_column(
        String(64), index=True, nullable=True
    )
    resource_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    ip_address: Mapped[str | None] = mapped_column(String(45), nullable=True)
    user_agent: Mapped[str | None] = mapped_column(String(255), nullable=True)
    request_id: Mapped[str | None] = mapped_column(
        String(64), index=True, nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utc_now,
        index=True,
        nullable=False,
    )

    @classmethod
    def record(
        cls,
        action: str,
        *,
        user_id: int | None = None,
        resource_type: str | None = None,
        resource_id: int | str | None = None,
        commit: bool = True,
    ) -> AuditLog:
        """Create and persist a security audit log entry with request context metadata."""
        ip_addr: str | None = None
        ua_str: str | None = None
        req_id: str | None = None

        if has_request_context():
            ip_addr = request.remote_addr
            ua_raw = request.headers.get("User-Agent", "")
            ua_str = ua_raw[:255] if ua_raw else None
            req_id = getattr(g, "request_id", None)

        entry = cls(
            user_id=user_id,
            action=action,
            resource_type=resource_type,
            resource_id=str(resource_id) if resource_id is not None else None,
            ip_address=ip_addr,
            user_agent=ua_str,
            request_id=req_id,
        )
        return entry.save(commit=commit)

