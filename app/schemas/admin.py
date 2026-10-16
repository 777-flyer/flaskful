"""Marshmallow schemas for Admin RBAC user management and security audit logs."""

from marshmallow import fields, validate

from app.schemas.auth import UserSchema
from app.schemas.common import BaseSchema, PaginationMetaSchema, PaginationQuerySchema

USER_ROLES = ("user", "admin")


class AuditLogSchema(BaseSchema):
    """Serialized AuditLog entry."""

    id = fields.Integer(dump_only=True)
    user_id = fields.Integer(dump_only=True, allow_none=True)
    action = fields.String(dump_only=True)
    resource_type = fields.String(dump_only=True, allow_none=True)
    resource_id = fields.String(dump_only=True, allow_none=True)
    ip_address = fields.String(dump_only=True, allow_none=True)
    user_agent = fields.String(dump_only=True, allow_none=True)
    request_id = fields.String(dump_only=True, allow_none=True)
    created_at = fields.DateTime(dump_only=True)


class AuditLogQuerySchema(PaginationQuerySchema):
    """Query parameters for filtering security audit logs."""

    action = fields.String(
        validate=validate.Length(min=1, max=64),
        metadata={"description": "Filter by audit action code (e.g., USER_LOGIN)."},
    )
    user_id = fields.Integer(
        validate=validate.Range(min=1),
        metadata={"description": "Filter by user ID."},
    )


class PaginatedAuditLogResponseSchema(BaseSchema):
    """Paginated response wrapper for security audit logs."""

    logs = fields.List(fields.Nested(AuditLogSchema), required=True)
    meta = fields.Nested(PaginationMetaSchema, required=True)


class AdminUserUpdateSchema(BaseSchema):
    """Payload schema for admin updates to a user's role, active status, or lockout state."""

    role = fields.String(
        validate=validate.OneOf(USER_ROLES),
        metadata={"example": "admin"},
    )
    is_active = fields.Boolean(
        metadata={"example": True},
    )
    unlock_account = fields.Boolean(
        load_default=False,
        metadata={"description": "Set true to reset failed login attempts and unlock."},
    )


class PaginatedUserResponseSchema(BaseSchema):
    """Paginated response wrapper for user accounts."""

    users = fields.List(fields.Nested(UserSchema), required=True)
    meta = fields.Nested(PaginationMetaSchema, required=True)
