"""Marshmallow schemas for Item CRUD operations and filtering."""

from marshmallow import fields, validate

from app.schemas.common import BaseSchema, PaginationMetaSchema, PaginationQuerySchema

ITEM_STATUSES = ("draft", "active", "archived")


class ItemSchema(BaseSchema):
    """Full serialized Item response schema."""

    id = fields.Integer(dump_only=True)
    title = fields.String(required=True)
    description = fields.String(allow_none=True)
    status = fields.String(required=True)
    owner_id = fields.Integer(dump_only=True)
    created_at = fields.DateTime(dump_only=True)
    updated_at = fields.DateTime(dump_only=True)


class ItemCreateSchema(BaseSchema):
    """Payload schema for creating a new Item."""

    title = fields.String(
        required=True,
        validate=validate.Length(min=1, max=150),
        metadata={"example": "Build frontend integration"},
    )
    description = fields.String(
        load_default=None,
        allow_none=True,
        validate=validate.Length(max=2000),
        metadata={"example": "Connect React/Vue frontend to the Flask REST API."},
    )
    status = fields.String(
        load_default="active",
        validate=validate.OneOf(ITEM_STATUSES),
        metadata={"example": "active"},
    )


class ItemUpdateSchema(BaseSchema):
    """Payload schema for updating an existing Item."""

    title = fields.String(
        validate=validate.Length(min=1, max=150),
        metadata={"example": "Updated item title"},
    )
    description = fields.String(
        allow_none=True,
        validate=validate.Length(max=2000),
        metadata={"example": "Updated description text."},
    )
    status = fields.String(
        validate=validate.OneOf(ITEM_STATUSES),
        metadata={"example": "archived"},
    )


class ItemQuerySchema(PaginationQuerySchema):
    """Query parameters for filtering and paginating Items."""

    status = fields.String(
        validate=validate.OneOf(ITEM_STATUSES),
        metadata={"description": "Filter items by status (draft, active, archived)."},
    )
    search = fields.String(
        validate=validate.Length(min=1, max=100),
        metadata={"description": "Case-insensitive search term in item title."},
    )


class PaginatedItemResponseSchema(BaseSchema):
    """Paginated response wrapper for a list of Items."""

    items = fields.List(fields.Nested(ItemSchema), required=True)
    meta = fields.Nested(PaginationMetaSchema, required=True)
