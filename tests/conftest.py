"""Pytest fixtures for testing the Flask REST API."""

import pytest

from app import create_app
from app.extensions import db, limiter


@pytest.fixture()
def app():
    """Create and configure a new app instance for each test."""
    test_app = create_app("testing")

    with test_app.app_context():
        limiter.reset()
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
    """Register a test user and return Authorization Bearer headers."""
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
