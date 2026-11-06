import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session, SQLModel, create_engine
from sqlmodel.pool import StaticPool

from src.infrastructure.db.session import get_session
from src.main import app
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
    yield authenticated_client(session)
    app.dependency_overrides.clear()


def test_user_can_read_and_update_preferred_language(client: TestClient) -> None:
    current = client.get("/api/v1/users/me")
    assert current.status_code == 200
    assert current.json()["preferred_language"] == "es"

    updated = client.patch(
        "/api/v1/users/me",
        json={"preferred_language": "en"},
    )
    assert updated.status_code == 200
    assert updated.json()["preferred_language"] == "en"
    assert client.get("/api/v1/users/me").json()["preferred_language"] == "en"


def test_user_language_rejects_unsupported_values(client: TestClient) -> None:
    response = client.patch(
        "/api/v1/users/me",
        json={"preferred_language": "fr"},
    )

    assert response.status_code == 422
