import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient
from sqlmodel import Session, SQLModel, create_engine
from sqlmodel.pool import StaticPool

from src.config import settings
from src.domain.locations.models import UserLocation
from src.infrastructure.db.session import get_session
from src.main import app
from src.routers import webhooks
from tests.auth_utils import create_test_user


def test_settings_load_webhook_secret_from_environment(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("WEBHOOK_SECRET", "configured-secret")

    configured = settings.__class__(_env_file=None)

    assert configured.webhook_secret == "configured-secret"


@pytest.fixture(name="session")
def session_fixture():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    SQLModel.metadata.create_all(engine)
    with Session(engine) as session:
        yield session
    SQLModel.metadata.drop_all(engine)


@pytest.fixture(name="client")
def client_fixture(session: Session):
    app.dependency_overrides[get_session] = lambda: session
    yield TestClient(app)
    app.dependency_overrides.clear()


def test_location_trigger_requires_configured_secret(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(settings, "webhook_secret", "test-secret")
    response = client.post(
        "/api/v1/webhooks/location-trigger",
        json={
            "user_id": "018e345a-2095-4ffc-8d86-b1cc41be954d",
            "location_id": "loc-parents-house",
            "trigger_type": "LOCATION_ENTER",
        },
        headers={"X-LanDo-Webhook-Secret": "wrong-secret"},
    )

    assert response.status_code == 401


def test_location_trigger_accepts_valid_secret(
    client: TestClient, monkeypatch: pytest.MonkeyPatch, session: Session
) -> None:
    monkeypatch.setattr(settings, "webhook_secret", "test-secret")
    user = create_test_user(session)
    location = UserLocation(
        user_id=user.id,
        name="Parents' house",
        latitude=40.0,
        longitude=-3.0,
    )
    session.add(location)
    session.commit()
    response = client.post(
        "/api/v1/webhooks/location-trigger",
        json={
            "user_id": str(user.id),
            "location_id": location.id,
            "trigger_type": "LOCATION_ENTER",
        },
        headers={"X-LanDo-Webhook-Secret": "test-secret"},
    )

    assert response.status_code == 200
    assert response.json()["message"] == "Location trigger received"


def test_location_trigger_accepts_legacy_secret_header(
    client: TestClient, monkeypatch: pytest.MonkeyPatch, session: Session
) -> None:
    monkeypatch.setattr(settings, "webhook_secret", "test-secret")
    user = create_test_user(session)
    location = UserLocation(
        user_id=user.id,
        name="Parents' house",
        latitude=40.0,
        longitude=-3.0,
    )
    session.add(location)
    session.commit()
    response = client.post(
        "/api/v1/webhooks/location-trigger",
        json={
            "user_id": str(user.id),
            "location_id": location.id,
            "trigger_type": "LOCATION_EXIT",
        },
        headers={"X-Webhook-Secret": "test-secret"},
    )

    assert response.status_code == 200


def test_location_trigger_cannot_cross_user_boundary(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
    session: Session,
) -> None:
    monkeypatch.setattr(settings, "webhook_secret", "test-secret")
    owner = create_test_user(session, "location-owner@example.com")
    other_user = create_test_user(session, "other-location-user@example.com")
    location = UserLocation(
        user_id=owner.id,
        name="Private location",
        latitude=40.0,
        longitude=-3.0,
    )
    session.add(location)
    session.commit()

    response = client.post(
        "/api/v1/webhooks/location-trigger",
        json={
            "user_id": str(other_user.id),
            "location_id": location.id,
            "trigger_type": "LOCATION_ENTER",
        },
        headers={"X-LanDo-Webhook-Secret": "test-secret"},
    )

    assert response.status_code == 404


def test_location_trigger_rejects_unknown_trigger_type(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(settings, "webhook_secret", "test-secret")
    response = client.post(
        "/api/v1/webhooks/location-trigger",
        json={
            "user_id": "018e345a-2095-4ffc-8d86-b1cc41be954d",
            "location_id": "loc-parents-house",
            "trigger_type": "ENTER",
        },
        headers={"X-LanDo-Webhook-Secret": "test-secret"},
    )

    assert response.status_code == 422


def test_location_trigger_rejects_blank_string_identifiers(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(settings, "webhook_secret", "test-secret")
    response = client.post(
        "/api/v1/webhooks/location-trigger",
        json={
            "user_id": " ",
            "location_id": "loc-parents-house",
            "trigger_type": "LOCATION_ENTER",
        },
        headers={"X-LanDo-Webhook-Secret": "test-secret"},
    )

    assert response.status_code == 422


def test_location_trigger_rejects_missing_secret_configuration(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(settings, "webhook_secret", "")
    response = client.post(
        "/api/v1/webhooks/location-trigger",
        json={
            "user_id": "018e345a-2095-4ffc-8d86-b1cc41be954d",
            "location_id": "loc-parents-house",
            "trigger_type": "LOCATION_ENTER",
        },
    )

    assert response.status_code == 503


def test_non_ascii_secret_mismatch_returns_unauthorized(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(settings, "webhook_secret", "test-secret")

    with pytest.raises(HTTPException) as exc_info:
        webhooks.verify_webhook_secret("ñ", None)

    assert exc_info.value.status_code == 401


def test_location_trigger_returns_structured_error_on_unexpected_exception(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(settings, "webhook_secret", "test-secret")

    def fail_processing(
        payload: webhooks.LocationTriggerRequest,
        session: Session,
    ) -> dict[str, str]:
        raise RuntimeError("location service unavailable")

    monkeypatch.setattr(webhooks, "_process_location_trigger", fail_processing)
    response = client.post(
        "/api/v1/webhooks/location-trigger",
        json={
            "user_id": "018e345a-2095-4ffc-8d86-b1cc41be954d",
            "location_id": "loc-parents-house",
            "trigger_type": "LOCATION_ENTER",
        },
        headers={"X-LanDo-Webhook-Secret": "test-secret"},
    )

    assert response.status_code == 500
    assert response.json()["detail"] == {
        "message": "Failed to process location trigger",
        "error": "location service unavailable",
    }


def test_external_event_returns_not_found_for_unknown_event(
    client: TestClient, monkeypatch: pytest.MonkeyPatch, session: Session
) -> None:
    monkeypatch.setattr(settings, "webhook_secret", "test-secret")
    user = create_test_user(session)
    response = client.post(
        "/api/v1/webhooks/external-event",
        json={
            "user_id": str(user.id),
            "event_id": "missing",
            "reminder_minutes": [15],
        },
        headers={"X-LanDo-Webhook-Secret": "test-secret"},
    )

    assert response.status_code == 404
