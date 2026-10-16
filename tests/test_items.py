"""Tests for Item CRUD, UUIDs, caching, dynamic sorting, soft delete/restore, and authorization."""


def test_items_crud_soft_delete_and_restore_lifecycle(client, auth_headers):
    """Authenticated user can create, sort, update, soft-delete, and restore items."""
    # 1. Create an item and verify public UUID is generated
    create_res = client.post(
        "/api/v1/items",
        headers=auth_headers,
        json={
            "title": "First API Task",
            "description": "Test item creation",
            "status": "active",
        },
    )
    assert create_res.status_code == 201
    item = create_res.get_json()
    item_id = item["id"]
    assert item["title"] == "First API Task"
    assert len(item["uuid"]) == 36
    assert item["deleted_at"] is None

    # 2. List items with dynamic sorting and pagination metadata
    list_res = client.get(
        "/api/v1/items?page=1&per_page=10&status=active&sort_by=title&sort_order=asc",
        headers=auth_headers,
    )
    assert list_res.status_code == 200
    list_data = list_res.get_json()
    assert len(list_data["items"]) == 1
    assert list_data["meta"]["total_items"] == 1

    # 3. Retrieve item by ID
    get_res = client.get(f"/api/v1/items/{item_id}", headers=auth_headers)
    assert get_res.status_code == 200
    assert get_res.get_json()["id"] == item_id

    # 4. Update item via PATCH (invalidates cache automatically)
    patch_res = client.patch(
        f"/api/v1/items/{item_id}",
        headers=auth_headers,
        json={"status": "archived", "title": "Updated API Task"},
    )
    assert patch_res.status_code == 200
    assert patch_res.get_json()["status"] == "archived"
    assert patch_res.get_json()["title"] == "Updated API Task"

    # 5. Soft-delete item
    del_res = client.delete(f"/api/v1/items/{item_id}", headers=auth_headers)
    assert del_res.status_code == 200

    # 6. Verify 404 when fetching soft-deleted item normally
    not_found_res = client.get(f"/api/v1/items/{item_id}", headers=auth_headers)
    assert not_found_res.status_code == 404
    assert not_found_res.get_json()["error"] == "NOT_FOUND"

    # 7. Verify soft-deleted item appears when include_deleted=true
    archived_list = client.get(
        "/api/v1/items?include_deleted=true", headers=auth_headers
    ).get_json()
    assert len(archived_list["items"]) == 1
    assert archived_list["items"][0]["deleted_at"] is not None

    # 8. Restore the soft-deleted item
    restore_res = client.post(
        f"/api/v1/items/{item_id}/restore", headers=auth_headers
    )
    assert restore_res.status_code == 200
    assert restore_res.get_json()["deleted_at"] is None


def test_items_require_authentication(client):
    """Protected item endpoints should reject unauthenticated requests with 401."""
    res = client.get("/api/v1/items")
    assert res.status_code == 401
    assert res.get_json()["error"] == "AUTHORIZATION_REQUIRED"
