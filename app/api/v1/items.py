"""Sample Item CRUD endpoints demonstrating caching, dynamic sorting, soft delete/restore, and BOLA protection."""

from flask.views import MethodView
from flask_jwt_extended import get_jwt_identity, jwt_required
from flask_smorest import Blueprint

from app.schemas.common import MessageSchema
from app.schemas.item import (
    ItemCreateSchema,
    ItemQuerySchema,
    ItemSchema,
    ItemUpdateSchema,
    PaginatedItemResponseSchema,
)
from app.services.item_service import ItemService

blp = Blueprint(
    "Items",
    __name__,
    url_prefix="/api/v1/items",
    description="CRUD, dynamic sorting, caching, and soft-delete operations for Item resources.",
)


@blp.route("")
class ItemListResource(MethodView):
    """Collection endpoint for listing and creating Items."""

    @jwt_required()
    @blp.doc(security=[{"BearerAuth": []}])
    @blp.arguments(ItemQuerySchema, location="query")
    @blp.response(200, PaginatedItemResponseSchema)
    def get(self, query_args: dict):
        """List paginated, dynamically sorted, and cached items belonging to the authenticated user."""
        owner_id = int(get_jwt_identity())
        return ItemService.list_items(
            owner_id=owner_id,
            page=query_args["page"],
            per_page=query_args["per_page"],
            status=query_args.get("status"),
            search=query_args.get("search"),
            sort_by=query_args.get("sort_by", "created_at"),
            sort_order=query_args.get("sort_order", "desc"),
            include_deleted=query_args.get("include_deleted", False),
        )

    @jwt_required()
    @blp.doc(security=[{"BearerAuth": []}])
    @blp.arguments(ItemCreateSchema)
    @blp.response(201, ItemSchema)
    def post(self, item_data: dict):
        """Create a new item for the authenticated user."""
        owner_id = int(get_jwt_identity())
        return ItemService.create_item(item_data, owner_id=owner_id)


@blp.route("/<int:item_id>")
class ItemDetailResource(MethodView):
    """Single item endpoint for retrieving, updating, and soft-deleting an Item."""

    @jwt_required()
    @blp.doc(security=[{"BearerAuth": []}])
    @blp.response(200, ItemSchema)
    def get(self, item_id: int):
        """Retrieve a specific item by ID."""
        owner_id = int(get_jwt_identity())
        return ItemService.get_item_for_owner(item_id, owner_id=owner_id)

    @jwt_required()
    @blp.doc(security=[{"BearerAuth": []}])
    @blp.arguments(ItemUpdateSchema)
    @blp.response(200, ItemSchema)
    def patch(self, update_data: dict, item_id: int):
        """Partially update an existing item by ID."""
        owner_id = int(get_jwt_identity())
        return ItemService.update_item(item_id, update_data, owner_id=owner_id)

    @jwt_required()
    @blp.doc(security=[{"BearerAuth": []}])
    @blp.response(200, MessageSchema)
    def delete(self, item_id: int):
        """Soft-delete (archive) an item by ID."""
        owner_id = int(get_jwt_identity())
        ItemService.delete_item(item_id, owner_id=owner_id)
        return {"status": "success", "message": f"Item {item_id} deleted successfully."}


@blp.route("/<int:item_id>/restore")
class ItemRestoreResource(MethodView):
    """Endpoint to restore a previously soft-deleted Item."""

    @jwt_required()
    @blp.doc(security=[{"BearerAuth": []}])
    @blp.response(200, ItemSchema)
    def post(self, item_id: int):
        """Restore a soft-deleted item by ID."""
        owner_id = int(get_jwt_identity())
        return ItemService.restore_item(item_id, owner_id=owner_id)
