"""Tests for the health check endpoint."""

from fastapi.testclient import TestClient

from src.main import app

client = TestClient(app)


def test_health_check() -> None:
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert body["service"] == "lando-api"
    assert "timestamp" in body


def test_root() -> None:
    response = client.get("/")
    assert response.status_code == 200
    assert "LanDo API" in response.json()["message"]


def test_api_routes_are_mounted_once_under_version_prefix() -> None:
    paths = set(app.openapi()["paths"])
    expected_paths = {
        "/api/v1/health",
        "/api/v1/chat",
        "/api/v1/events",
        "/api/v1/locations",
        "/api/v1/settings/llm",
        "/api/v1/webhooks/location-trigger",
        "/api/v1/webhooks/external-event",
    }

    assert expected_paths <= paths
    assert not any("/api/v1/api/" in path for path in paths)
