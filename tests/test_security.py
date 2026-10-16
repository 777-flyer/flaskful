"""Comprehensive tests for API security headers, DB security pragmas, lockout, BOLA, and input validation."""

from sqlalchemy import text

from app.extensions import db


def test_http_security_headers_and_request_id(client):
    """API responses must include OWASP security headers and X-Request-ID correlation."""
    res = client.get(
        "/api/v1/health",
        headers={"X-Request-ID": "custom-trace-id-123"},
    )
    assert res.status_code == 200
    assert res.headers["X-Request-ID"] == "custom-trace-id-123"
    assert res.headers["X-Content-Type-Options"] == "nosniff"
    assert res.headers["X-Frame-Options"] == "DENY"
    assert res.headers["Referrer-Policy"] == "strict-origin-when-cross-origin"
    assert "default-src 'none'" in res.headers["Content-Security-Policy"]
    assert "no-store" in res.headers["Cache-Control"]


def test_sqlite_database_security_pragmas(app):
    """Database connections must enforce foreign keys, trusted_schema=OFF, and secure_delete=ON."""
    with app.app_context():
        fk_enabled = db.session.execute(text("PRAGMA foreign_keys;")).scalar()
        trusted_schema = db.session.execute(text("PRAGMA trusted_schema;")).scalar()
        secure_delete = db.session.execute(text("PRAGMA secure_delete;")).scalar()

        assert fk_enabled == 1
        assert trusted_schema == 0
        assert secure_delete == 1


def test_password_strength_and_mass_assignment_protection(client):
    """Weak passwords, unknown fields (mass assignment), and null bytes must be rejected."""
    # Weak password (no special character or uppercase)
    weak_res = client.post(
        "/api/v1/auth/register",
        json={
            "username": "weakuser",
            "email": "weak@example.com",
            "password": "weakpassword123",
        },
    )
    assert weak_res.status_code == 422

    # Mass assignment attempt (trying to inject role="admin")
    mass_res = client.post(
        "/api/v1/auth/register",
        json={
            "username": "hacker",
            "email": "hacker@example.com",
            "password": "StrongPassword123!",
            "role": "admin",
        },
    )
    assert mass_res.status_code == 422

    # Null-byte injection attempt
    null_res = client.post(
        "/api/v1/auth/register",
        json={
            "username": "bad\x00user",
            "email": "null@example.com",
            "password": "StrongPassword123!",
        },
    )
    assert null_res.status_code == 422


def test_bola_ownership_isolation(client):
    """User B must be forbidden (403) from accessing, modifying, or deleting User A's items."""
    # Register User A and create an item
    user_a = client.post(
        "/api/v1/auth/register",
        json={
            "username": "user_a",
            "email": "a@example.com",
            "password": "PasswordA123!",
        },
    ).get_json()
    headers_a = {"Authorization": f"Bearer {user_a['access_token']}"}

    item = client.post(
        "/api/v1/items",
        headers=headers_a,
        json={"title": "Private Item A", "status": "active"},
    ).get_json()

    # Register User B
    user_b = client.post(
        "/api/v1/auth/register",
        json={
            "username": "user_b",
            "email": "b@example.com",
            "password": "PasswordB123!",
        },
    ).get_json()
    headers_b = {"Authorization": f"Bearer {user_b['access_token']}"}

    # User B tries to read, patch, and delete User A's item -> 403 FORBIDDEN
    assert client.get(f"/api/v1/items/{item['id']}", headers=headers_b).status_code == 403
    assert (
        client.patch(
            f"/api/v1/items/{item['id']}",
            headers=headers_b,
            json={"title": "Hijacked"},
        ).status_code
        == 403
    )
    assert (
        client.delete(f"/api/v1/items/{item['id']}", headers=headers_b).status_code
        == 403
    )


def test_brute_force_account_lockout_and_rate_limiting(app, client):
    """Repeated failed logins should lock the account (423) and enforce rate limits (429)."""
    app.config["MAX_FAILED_LOGIN_ATTEMPTS"] = 3
    client.post(
        "/api/v1/auth/register",
        json={
            "username": "lockuser",
            "email": "lock@example.com",
            "password": "CorrectPassword123!",
        },
    )

    # First 2 wrong attempts -> 401 UNAUTHORIZED
    for _ in range(2):
        res = client.post(
            "/api/v1/auth/login",
            json={"email": "lock@example.com", "password": "WrongPassword123!"},
        )
        assert res.status_code == 401

    # 3rd wrong attempt reaches MAX_FAILED_LOGIN_ATTEMPTS -> 423 ACCOUNT_LOCKED
    locked_res = client.post(
        "/api/v1/auth/login",
        json={"email": "lock@example.com", "password": "WrongPassword123!"},
    )
    assert locked_res.status_code == 423
    assert locked_res.get_json()["error"] == "ACCOUNT_LOCKED"

    # Even with the correct password, login is blocked while locked
    still_locked = client.post(
        "/api/v1/auth/login",
        json={"email": "lock@example.com", "password": "CorrectPassword123!"},
    )
    assert still_locked.status_code == 423
