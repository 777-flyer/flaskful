"""Item CRUD and query service layer with parameterized & wildcard-escaped queries."""

from __future__ import annotations

from typing import Any

from sqlalchemy import select

from app.core.exceptions import ForbiddenError, NotFoundError
from app.extensions import db
from app.models.item import Item


def _escape_like_wildcards(term: str) -> str:
    """Escape SQL LIKE/ILIKE wildcard characters (%, _, \\) in user search input."""
    return term.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")


class ItemService:
    """Encapsulates business logic and database queries for Item resources."""

    @staticmethod
    def list_items(
        *,
        owner_id: int,
        page: int = 1,
        per_page: int = 20,
        status: str | None = None,
        search: str | None = None,
    ) -> dict[str, Any]:
        """Return a paginated, filtered list of items belonging to owner_id."""
        stmt = select(Item).where(Item.owner_id == owner_id)

        if status:
            stmt = stmt.where(Item.status == status)

        if search:
            escaped_search = _escape_like_wildcards(search.strip())
            stmt = stmt.where(Item.title.ilike(f"%{escaped_search}%", escape="\\"))

        stmt = stmt.order_by(Item.created_at.desc(), Item.id.desc())

        pagination = db.paginate(
            stmt,
            page=page,
            per_page=per_page,
            error_out=False,
        )

        return {
            "items": pagination.items,
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
    def get_item_for_owner(item_id: int, owner_id: int) -> Item:
        """Fetch an item by ID and enforce strict object-level ownership (BOLA protection)."""
        item = db.session.get(Item, item_id)
        if item is None:
            raise NotFoundError(f"Item with id {item_id} was not found.")
        if item.owner_id != owner_id:
            raise ForbiddenError("You do not have permission to access this item.")
        return item

    @staticmethod
    def create_item(data: dict[str, Any], owner_id: int) -> Item:
        """Create and persist a new Item for the authenticated user."""
        item = Item(
            title=data["title"].strip(),
            description=data.get("description"),
            status=data.get("status", "active"),
            owner_id=owner_id,
        )
        return item.save()

    @staticmethod
    def update_item(item_id: int, data: dict[str, Any], owner_id: int) -> Item:
        """Update an existing Item after verifying ownership."""
        item = ItemService.get_item_for_owner(item_id, owner_id)

        if "title" in data:
            item.title = data["title"].strip()
        if "description" in data:
            item.description = data["description"]
        if "status" in data:
            item.status = data["status"]

        return item.save()

    @staticmethod
    def delete_item(item_id: int, owner_id: int) -> None:
        """Delete an Item after verifying ownership."""
        item = ItemService.get_item_for_owner(item_id, owner_id)
        item.delete()
