"""Admin RBAC endpoints for user management and security audit trail inspection."""

from flask.views import MethodView
from flask_jwt_extended import get_jwt_identity
from flask_smorest import Blueprint

from app.core.security import roles_required
from app.schemas.admin import (
    AdminUserUpdateSchema,
    AuditLogQuerySchema,
    PaginatedAuditLogResponseSchema,
    PaginatedUserResponseSchema,
)
from app.schemas.auth import UserSchema
from app.schemas.common import PaginationQuerySchema
from app.services.admin_service import AdminService

blp = Blueprint(
    "Admin",
    __name__,
    url_prefix="/api/v1/admin",
    description="Role-Based Access Control (RBAC) admin endpoints for user management and audit logs.",
)


@blp.route("/users")
class AdminUserListResource(MethodView):
    """Admin endpoint to list all user accounts."""

    @roles_required("admin")
    @blp.doc(security=[{"BearerAuth": []}])
    @blp.arguments(PaginationQuerySchema, location="query")
    @blp.response(200, PaginatedUserResponseSchema)
    def get(self, query_args: dict):
        """List paginated user accounts (requires admin role)."""
        return AdminService.list_users(
            page=query_args["page"],
            per_page=query_args["per_page"],
        )


@blp.route("/users/<int:user_id>")
class AdminUserDetailResource(MethodView):
    """Admin endpoint to update a user's role, active status, or lockout state."""

    @roles_required("admin")
    @blp.doc(security=[{"BearerAuth": []}])
    @blp.arguments(AdminUserUpdateSchema)
    @blp.response(200, UserSchema)
    def patch(self, update_data: dict, user_id: int):
        """Update user role, active status, or unlock account (requires admin role)."""
        admin_user_id = int(get_jwt_identity())
        return AdminService.update_user(
            target_user_id=user_id,
            data=update_data,
            admin_user_id=admin_user_id,
        )


@blp.route("/audit-logs")
class AdminAuditLogListResource(MethodView):
    """Admin endpoint to inspect the immutable security audit trail."""

    @roles_required("admin")
    @blp.doc(security=[{"BearerAuth": []}])
    @blp.arguments(AuditLogQuerySchema, location="query")
    @blp.response(200, PaginatedAuditLogResponseSchema)
    def get(self, query_args: dict):
        """List paginated security audit log entries (requires admin role)."""
        return AdminService.list_audit_logs(
            page=query_args["page"],
            per_page=query_args["per_page"],
            action=query_args.get("action"),
            user_id=query_args.get("user_id"),
        )

