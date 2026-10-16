"""Common reusable Marshmallow schemas with mass-assignment & null-byte injection protection."""

from __future__ import annotations

from typing import Any

from marshmallow import RAISE, Schema, ValidationError, fields, pre_load, validate


class BaseSchema(Schema):
    """Hardened base schema rejecting unknown fields and null-byte control characters."""

    class Meta:
        unknown = RAISE

    @pre_load
    def sanitize_strings(self, data: Any, **kwargs) -> Any:
        """Reject null bytes in string inputs to prevent injection/truncation attacks."""
        if not isinstance(data, dict):
            return data
        for key, value in data.items():
            if isinstance(value, str) and "\x00" in value:
                raise ValidationError(
                    {key: ["Input contains forbidden null-byte characters."]}
                )
        return data


class MessageSchema(BaseSchema):
    """Standard simple message response schema."""

    status = fields.String(dump_default="success", metadata={"example": "success"})
    message = fields.String(required=True, metadata={"example": "Operation completed."})


class HealthResponseSchema(BaseSchema):
    """Health check endpoint response schema."""

    status = fields.String(required=True, metadata={"example": "healthy"})
    environment = fields.String(required=True, metadata={"example": "development"})
    database = fields.String(required=True, metadata={"example": "connected"})
    version = fields.String(required=True, metadata={"example": "v1"})


class PaginationQuerySchema(BaseSchema):
    """Standard query parameters for paginated list endpoints."""

    page = fields.Integer(
        load_default=1,
        validate=validate.Range(min=1, max=10000),
        metadata={"description": "Page number (1-indexed)."},
    )
    per_page = fields.Integer(
        load_default=20,
        validate=validate.Range(min=1, max=100),
        metadata={"description": "Number of items per page (max 100)."},
    )


class PaginationMetaSchema(BaseSchema):
    """Pagination metadata returned in list responses."""

    page = fields.Integer(required=True, metadata={"example": 1})
    per_page = fields.Integer(required=True, metadata={"example": 20})
    total_items = fields.Integer(required=True, metadata={"example": 42})
    total_pages = fields.Integer(required=True, metadata={"example": 3})
    has_next = fields.Boolean(required=True, metadata={"example": True})
    has_prev = fields.Boolean(required=True, metadata={"example": False})
