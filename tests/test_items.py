"""Tests for Item CRUD, pagination, filtering, and authorization."""


def test_items_crud_lifecycle(client, auth_headers):
    """Authenticated user can create, list, filter, update, and delete items."""
    # 1. Create an item
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

    # 2. List items with pagination metadata
    list_res = client.get(
        "/api/v1/items?page=1&per_page=10&status=active",
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

    # 4. Update item via PATCH
    patch_res = client.patch(
        f"/api/v1/items/{item_id}",
        headers=auth_headers,
        json={"status": "archived", "title": "Updated API Task"},
    )
    assert patch_res.status_code == 200
    assert patch_res.get_json()["status"] == "archived"
    assert patch_res.get_json()["title"] == "Updated API Task"

    # 5. Delete item
    del_res = client.delete(f"/api/v1/items/{item_id}", headers=auth_headers)
    assert del_res.status_code == 200

    # 6. Verify 404 after deletion
    not_found_res = client.get(f"/api/v1/items/{item_id}", headers=auth_headers)
    assert not_found_res.status_code == 404
    assert not_found_res.get_json()["error"] == "NOT_FOUND"


def test_items_require_authentication(client):
    """Protected item endpoints should reject unauthenticated requests with 401."""
    res = client.get("/api/v1/items")
    assert res.status_code == 401
    assert res.get_json()["error"] == "AUTHORIZATION_REQUIRED"

