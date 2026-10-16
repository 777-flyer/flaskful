"""Pytest fixtures for testing the FlaskFul REST API."""

import pytest

from app import create_app
from app.extensions import cache, db, limiter
from app.models.user import User


@pytest.fixture()
def app():
    """Create and configure a new app instance for each test."""
    test_app = create_app("testing")

    with test_app.app_context():
        limiter.reset()
        cache.clear()
        db.create_all()
        yield test_app
        db.session.remove()
        db.drop_all()


@pytest.fixture()
def client(app):
    """Test client for the Flask application."""
    return app.test_client()


@pytest.fixture()
def auth_headers(client):
    """Register a standard test user and return Authorization Bearer headers."""
    response = client.post(
        "/api/v1/auth/register",
        json={
            "username": "testuser",
            "email": "test@example.com",
            "password": "TestPassword123!",
        },
    )
    data = response.get_json()
    token = data["access_token"]
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture()
def admin_headers(app, client):
    """Create an admin user and return Authorization Bearer headers."""
    with app.app_context():
        admin = User(username="adminuser", email="admin@example.com", role="admin")
        admin.set_password("AdminPassword123!")
        admin.save()

    response = client.post(
        "/api/v1/auth/login",
        json={
            "email": "admin@example.com",
            "password": "AdminPassword123!",
        },
    )
    token = response.get_json()["access_token"]
    return {"Authorization": f"Bearer {token}"}
