from datetime import datetime, timezone

import jwt
import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session, SQLModel, create_engine
from sqlmodel.pool import StaticPool

from src.config import settings
from src.domain.users.models import User
from src.infrastructure.db.session import get_session
from src.main import app
from src.security.auth import create_access_token
from tests.auth_utils import authenticated_client, create_test_user


@pytest.fixture(name="session")
def session_fixture():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    SQLModel.metadata.create_all(engine)
    with Session(engine) as session:
        create_test_user(session)
        yield session
    SQLModel.metadata.drop_all(engine)


@pytest.fixture(name="client")
def client_fixture(session: Session):
    app.dependency_overrides[get_session] = lambda: session
    client = authenticated_client(session)
    yield client
    app.dependency_overrides.clear()


def _token_for_user(user: User) -> str:
    return create_access_token(user.id)


def test_register_login_and_jwt_user_claim(client: TestClient) -> None:
    registered = client.post(
        "/api/v1/auth/register",
        json={"email": "new-user@example.com", "password": "secure-password"},
    )
    assert registered.status_code == 201
    user = registered.json()
    assert user["email"] == "new-user@example.com"
    assert "hashed_password" not in user

    login = client.post(
        "/api/v1/auth/login",
        json={"email": "NEW-USER@example.com", "password": "secure-password"},
    )
    assert login.status_code == 200
    token = login.json()["access_token"]
    claims = jwt.decode(token, settings.secret_key, algorithms=["HS256"])
    assert claims["user_id"] == user["id"]
    assert claims["sub"] == user["id"]

    protected = client.get(
        "/api/v1/events",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert protected.status_code == 200


def test_registration_rejects_duplicate_email_and_bad_login(client: TestClient) -> None:
    response = client.post(
        "/api/v1/auth/register",
        json={"email": "duplicate@example.com", "password": "secure-password"},
    )
    assert response.status_code == 201

    duplicate = client.post(
        "/api/v1/auth/register",
        json={"email": "DUPLICATE@example.com", "password": "another-password"},
    )
    assert duplicate.status_code == 409

    invalid_login = client.post(
        "/api/v1/auth/login",
        json={"email": "duplicate@example.com", "password": "wrong-password"},
    )
    assert invalid_login.status_code == 401


def test_protected_routes_reject_missing_and_invalid_tokens(client: TestClient) -> None:
    assert client.get("/api/v1/events", headers={"Authorization": ""}).status_code == 401
    assert (
        client.get(
            "/api/v1/locations",
            headers={"Authorization": "Bearer invalid-token"},
        ).status_code
        == 401
    )
    assert (
        client.post(
            "/api/v1/chat",
            json={"message": "Hello"},
            headers={"Authorization": ""},
        ).status_code
        == 401
    )
    assert client.get("/api/v1/settings/llm", headers={"Authorization": ""}).status_code == 401
    assert client.get("/api/v1/health").status_code == 200


def test_events_and_settings_are_isolated_between_users(
    client: TestClient,
    session: Session,
) -> None:
    second_user = User(
        email="second-tenant@example.com",
        hashed_password="unused-test-password-hash",
    )
    session.add(second_user)
    session.commit()
    second_token = _token_for_user(second_user)

    created = client.post(
        "/api/v1/events",
        json={
            "title": "Private event",
            "start_time": datetime.now(timezone.utc).isoformat(),
        },
    )
    assert created.status_code == 201
    event_id = created.json()["id"]

    second_headers = {"Authorization": f"Bearer {second_token}"}
    assert client.get("/api/v1/events", headers=second_headers).json() == []
    assert client.get(f"/api/v1/events/{event_id}", headers=second_headers).status_code == 404

    first_settings = client.get("/api/v1/settings/llm").json()
    second_settings = client.get("/api/v1/settings/llm", headers=second_headers).json()
    assert first_settings["selected_model"] == second_settings["selected_model"]

    changed = client.put(
        "/api/v1/settings/llm",
        headers=second_headers,
        json={"selected_provider": "google", "selected_model": "tenant-model"},
    )
    assert changed.status_code == 200
    assert client.get("/api/v1/settings/llm").json()["selected_provider"] == "ollama"
    assert (
        client.get("/api/v1/settings/llm", headers=second_headers).json()["selected_provider"]
        == "google"
    )
