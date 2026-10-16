"""Marshmallow schemas for authentication, password policy enforcement, and user serialization."""

import re

from marshmallow import ValidationError, fields, validate

from app.schemas.common import BaseSchema

USERNAME_PATTERN = re.compile(r"^[a-zA-Z0-9_-]{3,80}$")


def validate_password_strength(password: str) -> None:
    """Enforce OWASP password complexity requirements."""
    errors: list[str] = []
    if len(password) < 8 or len(password) > 128:
        errors.append("Password must be between 8 and 128 characters long.")
    if not any(ch.isupper() for ch in password):
        errors.append("Password must contain at least one uppercase letter.")
    if not any(ch.islower() for ch in password):
        errors.append("Password must contain at least one lowercase letter.")
    if not any(ch.isdigit() for ch in password):
        errors.append("Password must contain at least one digit.")
    if not any(not ch.isalnum() for ch in password):
        errors.append("Password must contain at least one special character.")
    if errors:
        raise ValidationError(errors)


def validate_username_format(username: str) -> None:
    """Ensure username contains only safe alphanumeric, underscore, or hyphen characters."""
    if not USERNAME_PATTERN.match(username.strip()):
        raise ValidationError(
            "Username must be 3-80 characters and contain only letters, digits, underscores, or hyphens."
        )


class UserSchema(BaseSchema):
    """Serialized User representation (never exposes password_hash or lockout internals)."""

    id = fields.Integer(dump_only=True)
    username = fields.String(required=True)
    email = fields.Email(required=True)
    role = fields.String(dump_only=True)
    is_active = fields.Boolean(dump_only=True)
    created_at = fields.DateTime(dump_only=True)
    updated_at = fields.DateTime(dump_only=True)


class UserRegisterSchema(BaseSchema):
    """Payload schema for registering a new user account."""

    username = fields.String(
        required=True,
        validate=validate_username_format,
        metadata={"example": "johndoe"},
    )
    email = fields.Email(
        required=True,
        validate=validate.Length(max=120),
        metadata={"example": "john@example.com"},
    )
    password = fields.String(
        required=True,
        load_only=True,
        validate=validate_password_strength,
        metadata={"example": "StrongPass123!"},
    )


class UserLoginSchema(BaseSchema):
    """Payload schema for authenticating an existing user."""

    email = fields.Email(
        required=True,
        validate=validate.Length(max=120),
        metadata={"example": "john@example.com"},
    )
    password = fields.String(
        required=True,
        load_only=True,
        validate=validate.Length(min=1, max=128),
        metadata={"example": "StrongPass123!"},
    )


class PasswordChangeSchema(BaseSchema):
    """Payload schema for changing the authenticated user's password."""

    current_password = fields.String(
        required=True,
        load_only=True,
        validate=validate.Length(min=1, max=128),
    )
    new_password = fields.String(
        required=True,
        load_only=True,
        validate=validate_password_strength,
    )


class AuthTokenResponseSchema(BaseSchema):
    """Response schema returning user details alongside JWT access and refresh tokens."""

    access_token = fields.String(required=True)
    refresh_token = fields.String(required=True)
    token_type = fields.String(dump_default="Bearer", metadata={"example": "Bearer"})
    user = fields.Nested(UserSchema, required=True)


class TokenRotationResponseSchema(BaseSchema):
    """Response schema for token refresh endpoint with rotated refresh token."""

    access_token = fields.String(required=True)
    refresh_token = fields.String(required=True)
    token_type = fields.String(dump_default="Bearer", metadata={"example": "Bearer"})
