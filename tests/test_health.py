"""Tests for root discovery and health check endpoints."""


def test_root_discovery(client):
    """Root endpoint should return API metadata and documentation links."""
    response = client.get("/")
    assert response.status_code == 200
    data = response.get_json()
    assert data["version"] == "v1"
    assert data["docs_url"] == "/docs"
    assert data["health_url"] == "/api/v1/health"


def test_health_check(client):
    """Health check endpoint should verify database connectivity."""
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    data = response.get_json()
    assert data["status"] == "healthy"
    assert data["database"] == "connected"
    assert data["environment"] == "testing"

