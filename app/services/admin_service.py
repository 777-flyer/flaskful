"""Admin RBAC user management and security audit trail query service."""

from __future__ import annotations

from typing import Any

from sqlalchemy import select

from app.core.exceptions import APIError, NotFoundError
from app.extensions import db
from app.models.audit_log import AuditLog
from app.models.user import User


class AdminService:
    """Encapsulates administrative operations protected by RBAC (@roles_required('admin'))."""

    @staticmethod
    def list_users(*, page: int = 1, per_page: int = 20) -> dict[str, Any]:
        """Return a paginated list of all registered user accounts."""
        stmt = select(User).order_by(User.created_at.desc(), User.id.desc())
        pagination = db.paginate(stmt, page=page, per_page=per_page, error_out=False)
        return {
            "users": pagination.items,
            "meta": {
                "page": pagination.page,
                "per_page": pagination.per_page,
                "total_items": pagination.total,
                "total_pages": pagination.pages,
                "has_next": pagination.has_next,
                "has_prev": pagination.has_prev,
            },
        }

    @staticmethod
    def update_user(
        target_user_id: int, data: dict[str, Any], admin_user_id: int
    ) -> User:
        """Update a user's role, active status, or lockout state."""
        user = db.session.get(User, target_user_id)
        if user is None:
            raise NotFoundError(f"User with id {target_user_id} was not found.")

        if target_user_id == admin_user_id:
            if data.get("is_active") is False:
                raise APIError(
                    "Administrators cannot deactivate their own account.",
                    status_code=400,
                    error_code="SELF_DEACTIVATION_FORBIDDEN",
                )
            if "role" in data and data["role"] != "admin":
                raise APIError(
                    "Administrators cannot demote their own role.",
                    status_code=400,
                    error_code="SELF_DEMOTION_FORBIDDEN",
                )

        if "role" in data:
            user.role = data["role"]
        if "is_active" in data:
            user.is_active = data["is_active"]
        if data.get("unlock_account"):
            user.failed_login_attempts = 0
            user.locked_until = None

        user.save()
        AuditLog.record(
            "ADMIN_USER_UPDATE",
            user_id=admin_user_id,
            resource_type="user",
            resource_id=user.id,
        )
        return user

    @staticmethod
    def list_audit_logs(
        *,
        page: int = 1,
        per_page: int = 20,
        action: str | None = None,
        user_id: int | None = None,
    ) -> dict[str, Any]:
        """Return a paginated, filtered list of security audit log entries."""
        stmt = select(AuditLog)

        if action:
            stmt = stmt.where(AuditLog.action == action.strip().upper())
        if user_id is not None:
            stmt = stmt.where(AuditLog.user_id == user_id)

        stmt = stmt.order_by(AuditLog.created_at.desc(), AuditLog.id.desc())
        pagination = db.paginate(stmt, page=page, per_page=per_page, error_out=False)

        return {
            "logs": pagination.items,
            "meta": {
                "page": pagination.page,
                "per_page": pagination.per_page,
                "total_items": pagination.total,
                "total_pages": pagination.pages,
                "has_next": pagination.has_next,
                "has_prev": pagination.has_prev,
            },
        }

