"""Tests for the health check endpoint."""

import pytest
from fastapi.testclient import TestClient

from src.main import app

client = TestClient(app)


def test_health_check() -> None:
    response = client.get("/health")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert body["service"] == "lando-api"
    assert "timestamp" in body


def test_root() -> None:
    response = client.get("/")
    assert response.status_code == 200
    assert "LanDo API" in response.json()["message"]
