"""Marshmallow schemas for Item CRUD operations, dynamic sorting, and filtering."""

from marshmallow import fields, validate

from app.schemas.common import BaseSchema, PaginationMetaSchema, PaginationQuerySchema

ITEM_STATUSES = ("draft", "active", "archived")
ITEM_SORT_FIELDS = ("created_at", "updated_at", "title", "status")
SORT_ORDERS = ("asc", "desc")


class ItemSchema(BaseSchema):
    """Full serialized Item response schema with public UUID and soft-delete timestamp."""

    id = fields.Integer(dump_only=True)
    uuid = fields.String(dump_only=True)
    title = fields.String(required=True)
    description = fields.String(allow_none=True)
    status = fields.String(required=True)
    owner_id = fields.Integer(dump_only=True)
    created_at = fields.DateTime(dump_only=True)
    updated_at = fields.DateTime(dump_only=True)
    deleted_at = fields.DateTime(dump_only=True, allow_none=True)


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
        metadata={"example": "Connect React/Vue frontend to the FlaskFul REST API."},
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
    """Query parameters for filtering, dynamic sorting, and paginating Items."""

    status = fields.String(
        validate=validate.OneOf(ITEM_STATUSES),
        metadata={"description": "Filter items by status (draft, active, archived)."},
    )
    search = fields.String(
        validate=validate.Length(min=1, max=100),
        metadata={"description": "Case-insensitive search term in item title."},
    )
    sort_by = fields.String(
        load_default="created_at",
        validate=validate.OneOf(ITEM_SORT_FIELDS),
        metadata={
            "description": "Field to sort by (created_at, updated_at, title, status)."
        },
    )
    sort_order = fields.String(
        load_default="desc",
        validate=validate.OneOf(SORT_ORDERS),
        metadata={"description": "Sort direction (asc or desc)."},
    )
    include_deleted = fields.Boolean(
        load_default=False,
        metadata={"description": "Include soft-deleted (archived) items."},
    )


class PaginatedItemResponseSchema(BaseSchema):
    """Paginated response wrapper for a list of Items."""

    items = fields.List(fields.Nested(ItemSchema), required=True)
    meta = fields.Nested(PaginationMetaSchema, required=True)
