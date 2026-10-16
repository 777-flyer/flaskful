"""Tests for JWT authentication, token rotation, logout, and password change."""


def test_register_login_rotate_and_logout_flow(client):
    """User can register, log in, rotate refresh tokens (single-use), and log out."""
    # 1. Register
    reg_res = client.post(
        "/api/v1/auth/register",
        json={
            "username": "alice",
            "email": "alice@example.com",
            "password": "AlicePassword123!",
        },
    )
    assert reg_res.status_code == 201
    reg_data = reg_res.get_json()
    assert "access_token" in reg_data
    assert "refresh_token" in reg_data
    assert reg_data["user"]["username"] == "alice"
    assert reg_data["user"]["role"] == "user"

    # 2. Duplicate registration should return 409 Conflict
    dup_res = client.post(
        "/api/v1/auth/register",
        json={
            "username": "alice2",
            "email": "alice@example.com",
            "password": "AlicePassword123!",
        },
    )
    assert dup_res.status_code == 409
    assert dup_res.get_json()["error"] == "CONFLICT"

    # 3. Login
    login_res = client.post(
        "/api/v1/auth/login",
        json={
            "email": "alice@example.com",
            "password": "AlicePassword123!",
        },
    )
    assert login_res.status_code == 200
    tokens = login_res.get_json()

    # 4. Fetch current user (/me)
    me_res = client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {tokens['access_token']}"},
    )
    assert me_res.status_code == 200
    assert me_res.get_json()["email"] == "alice@example.com"

    # 5. Rotate refresh token (returns both new access_token and new refresh_token)
    old_refresh = tokens["refresh_token"]
    refresh_res = client.post(
        "/api/v1/auth/refresh",
        headers={"Authorization": f"Bearer {old_refresh}"},
    )
    assert refresh_res.status_code == 200
    rotated = refresh_res.get_json()
    assert "access_token" in rotated
    assert "refresh_token" in rotated

    # 6. Reusing the old refresh token must fail with 401 TOKEN_REVOKED
    reuse_res = client.post(
        "/api/v1/auth/refresh",
        headers={"Authorization": f"Bearer {old_refresh}"},
    )
    assert reuse_res.status_code == 401
    assert reuse_res.get_json()["error"] == "TOKEN_REVOKED"

    # 7. Logout revokes the current access token
    logout_res = client.post(
        "/api/v1/auth/logout",
        headers={"Authorization": f"Bearer {rotated['access_token']}"},
    )
    assert logout_res.status_code == 200

    # 8. Using the logged-out access token must fail with 401 TOKEN_REVOKED
    after_logout_res = client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {rotated['access_token']}"},
    )
    assert after_logout_res.status_code == 401
    assert after_logout_res.get_json()["error"] == "TOKEN_REVOKED"
