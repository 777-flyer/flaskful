"""Item CRUD, caching, soft-delete, dynamic sorting, and query service layer."""

from __future__ import annotations

from typing import Any

from sqlalchemy import select

from app.core.exceptions import ForbiddenError, NotFoundError
from app.extensions import cache, db
from app.models.audit_log import AuditLog
from app.models.item import Item

SORTABLE_COLUMNS = {
    "created_at": Item.created_at,
    "updated_at": Item.updated_at,
    "title": Item.title,
    "status": Item.status,
}


def _escape_like_wildcards(term: str) -> str:
    """Escape SQL LIKE/ILIKE wildcard characters (%, _, \\) in user search input."""
    return term.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")


class ItemService:
    """Encapsulates business logic, caching, soft-delete, and dynamic queries for Items."""

    @staticmethod
    def _get_cache_version(owner_id: int) -> int:
        """Return the current cache namespace version for a given owner."""
        ver = cache.get(f"user_items_ver:{owner_id}")
        if ver is None:
            cache.set(f"user_items_ver:{owner_id}", 1, timeout=3600)
            return 1
        return int(ver)

    @staticmethod
    def invalidate_user_cache(owner_id: int) -> None:
        """Increment the owner's cache version to invalidate all cached item list queries."""
        ver = ItemService._get_cache_version(owner_id)
        cache.set(f"user_items_ver:{owner_id}", ver + 1, timeout=3600)

    @staticmethod
    def list_items(
        *,
        owner_id: int,
        page: int = 1,
        per_page: int = 20,
        status: str | None = None,
        search: str | None = None,
        sort_by: str = "created_at",
        sort_order: str = "desc",
        include_deleted: bool = False,
    ) -> dict[str, Any]:
        """Return a paginated, dynamically sorted, and cached list of items."""
        ver = ItemService._get_cache_version(owner_id)
        cache_key = (
            f"items:{owner_id}:v{ver}:p{page}:pp{per_page}:"
            f"st{status}:q{search}:sb{sort_by}:so{sort_order}:del{include_deleted}"
        )
        cached_result = cache.get(cache_key)
        if cached_result is not None:
            return cached_result

        stmt = select(Item).where(Item.owner_id == owner_id)

        if not include_deleted:
            stmt = stmt.where(Item.deleted_at.is_(None))

        if status:
            stmt = stmt.where(Item.status == status)

        if search:
            escaped_search = _escape_like_wildcards(search.strip())
            stmt = stmt.where(Item.title.ilike(f"%{escaped_search}%", escape="\\"))

        sort_col = SORTABLE_COLUMNS.get(sort_by, Item.created_at)
        if sort_order.lower() == "asc":
            stmt = stmt.order_by(sort_col.asc(), Item.id.asc())
        else:
            stmt = stmt.order_by(sort_col.desc(), Item.id.desc())

        pagination = db.paginate(
            stmt,
            page=page,
            per_page=per_page,
            error_out=False,
        )

        result = {
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
        cache.set(cache_key, result)
        return result

    @staticmethod
    def get_item_for_owner(
        item_id: int, owner_id: int, *, include_deleted: bool = False
    ) -> Item:
        """Fetch an item by ID and enforce strict object-level ownership (BOLA protection)."""
        item = db.session.get(Item, item_id)
        if item is None or (item.is_deleted and not include_deleted):
            raise NotFoundError(f"Item with id {item_id} was not found.")
        if item.owner_id != owner_id:
            raise ForbiddenError("You do not have permission to access this item.")
        return item

    @staticmethod
    def create_item(data: dict[str, Any], owner_id: int) -> Item:
        """Create a new Item, invalidate cache, and record an audit log."""
        item = Item(
            title=data["title"].strip(),
            description=data.get("description"),
            status=data.get("status", "active"),
            owner_id=owner_id,
        )
        item.save()
        ItemService.invalidate_user_cache(owner_id)
        AuditLog.record(
            "ITEM_CREATE",
            user_id=owner_id,
            resource_type="item",
            resource_id=item.id,
        )
        return item

    @staticmethod
    def update_item(item_id: int, data: dict[str, Any], owner_id: int) -> Item:
        """Update an existing Item, invalidate cache, and record an audit log."""
        item = ItemService.get_item_for_owner(item_id, owner_id)

        if "title" in data:
            item.title = data["title"].strip()
        if "description" in data:
            item.description = data["description"]
        if "status" in data:
            item.status = data["status"]

        item.save()
        ItemService.invalidate_user_cache(owner_id)
        AuditLog.record(
            "ITEM_UPDATE",
            user_id=owner_id,
            resource_type="item",
            resource_id=item.id,
        )
        return item

    @staticmethod
    def delete_item(item_id: int, owner_id: int) -> None:
        """Soft-delete an Item, invalidate cache, and record an audit log."""
        item = ItemService.get_item_for_owner(item_id, owner_id)
        item.soft_delete()
        ItemService.invalidate_user_cache(owner_id)
        AuditLog.record(
            "ITEM_SOFT_DELETE",
            user_id=owner_id,
            resource_type="item",
            resource_id=item.id,
        )

    @staticmethod
    def restore_item(item_id: int, owner_id: int) -> Item:
        """Restore a previously soft-deleted Item and invalidate cache."""
        item = ItemService.get_item_for_owner(
            item_id, owner_id, include_deleted=True
        )
        item.restore()
        ItemService.invalidate_user_cache(owner_id)
        AuditLog.record(
            "ITEM_RESTORE",
            user_id=owner_id,
            resource_type="item",
            resource_id=item.id,
        )
        return item
