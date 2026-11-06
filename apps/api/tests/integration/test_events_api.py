"""Integration tests for Events API and Database persistence."""

from datetime import UTC, datetime, timedelta

import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session, SQLModel, create_engine, select
from sqlmodel.pool import StaticPool

from src.infrastructure.db.models import EventOutboxModel, UserModel
from src.infrastructure.db.session import get_session
from src.main import app
from src.security.auth import create_access_token
from tests.auth_utils import authenticated_client, create_test_user


@pytest.fixture(name="session")
def session_fixture():
    """In-memory SQLite database session fixture for integration testing."""
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
    """TestClient fixture overriding the database session dependency."""

    def get_session_override():
        return session

    app.dependency_overrides[get_session] = get_session_override
    client = authenticated_client(session)
    yield client
    app.dependency_overrides.clear()


def _iso(dt: datetime) -> str:
    return dt.isoformat()


class TestEventsApiIntegration:
    def test_create_and_get_event(self, client: TestClient, session: Session):
        start = datetime.now(UTC) + timedelta(days=1)
        end = start + timedelta(hours=1)
        payload = {
            "title": "Architecture Sync",
            "description": "Deep-dive into Event-driven architecture",
            "start_time": _iso(start),
            "end_time": _iso(end),
            "is_all_day": False,
            "source": "LOCAL",
            "energy_level": "HIGH_ENERGY",
            "cognitive_load": 4,
            "dopamine_reward": "HIGH",
            "reminder_minutes": [15, 60],
        }

        # 1. POST /events
        response = client.post("/api/v1/events", json=payload)
        assert response.status_code == 201
        data = response.json()
        assert data["title"] == "Architecture Sync"
        assert data["cognitive_load"] == 4
        assert data["is_read_only"] is False
        event_id = data["id"]
        outbox_events = session.exec(select(EventOutboxModel)).all()
        assert len(outbox_events) == 1
        assert outbox_events[0].event_type == "event.created"
        assert outbox_events[0].payload["aggregate_id"] == event_id

        # 2. GET /events/{id}
        get_res = client.get(f"/api/v1/events/{event_id}")
        assert get_res.status_code == 200
        get_data = get_res.json()
        assert get_data["id"] == event_id
        assert get_data["description"] == "Deep-dive into Event-driven architecture"

        # 3. GET /events (list)
        list_res = client.get("/api/v1/events")
        assert list_res.status_code == 200
        list_data = list_res.json()
        assert len(list_data) >= 1
        assert any(e["id"] == event_id for e in list_data)

    def test_create_event_invalid_cognitive_load(self, client: TestClient):
        start = datetime.now(UTC)
        payload = {
            "title": "Invalid Task",
            "start_time": _iso(start),
            "cognitive_load": 10,  # exceeds max 5
        }
        response = client.post("/api/v1/events", json=payload)
        assert response.status_code == 422

    def test_reschedule_local_event_success(self, client: TestClient, session: Session):
        start = datetime.now(UTC) + timedelta(hours=2)
        create_res = client.post(
            "/api/v1/events",
            json={
                "title": "Team Sync",
                "start_time": _iso(start),
            },
        )
        assert create_res.status_code == 201
        event_id = create_res.json()["id"]

        # Reschedule
        new_start = start + timedelta(days=1)
        resched_res = client.post(
            f"/api/v1/events/{event_id}/reschedule",
            json={"new_start_time": _iso(new_start)},
        )
        assert resched_res.status_code == 200
        outbox_events = session.exec(select(EventOutboxModel)).all()
        assert sorted(event.event_type for event in outbox_events) == [
            "event.created",
            "event.rescheduled",
        ]

        # Verify new start time
        get_res = client.get(f"/api/v1/events/{event_id}")
        assert get_res.status_code == 200
        assert get_res.json()["start_time"].startswith(new_start.isoformat()[:19])

    def test_reschedule_read_only_event_forbidden(self, client: TestClient):
        start = datetime.now(UTC)
        # Create external event (source=GOOGLE_CALENDAR -> is_read_only=True)
        create_res = client.post(
            "/api/v1/events",
            json={
                "title": "Google Cal Meeting",
                "start_time": _iso(start),
                "source": "GOOGLE_CALENDAR",
            },
        )
        assert create_res.status_code == 201
        event_id = create_res.json()["id"]
        assert create_res.json()["is_read_only"] is True

        # Attempt to reschedule -> must return 403 Forbidden due to ImmutableEventException
        new_start = start + timedelta(days=1)
        resched_res = client.post(
            f"/api/v1/events/{event_id}/reschedule",
            json={"new_start_time": _iso(new_start)},
        )
        assert resched_res.status_code == 403
        assert (
            "is read-only because it originates from 'GOOGLE_CALENDAR'"
            in resched_res.json()["detail"]
        )

    def test_get_nonexistent_event_returns_404(self, client: TestClient):
        res = client.get("/api/v1/events/nonexistent-id-123")
        assert res.status_code == 404

    def test_event_reads_are_scoped_to_the_authenticated_user(
        self,
        client: TestClient,
        session: Session,
    ):
        start = datetime.now(UTC) + timedelta(days=1)
        created = client.post(
            "/api/v1/events",
            json={"title": "Private event", "start_time": _iso(start)},
        )
        assert created.status_code == 201

        other_user = UserModel(
            email="events-other-user@example.com",
            hashed_password="unused",
        )
        session.add(other_user)
        session.commit()
        other_headers = {"Authorization": f"Bearer {create_access_token(other_user.id)}"}

        assert client.get("/api/v1/events", headers=other_headers).json() == []
        assert (
            client.get(
                f"/api/v1/events/{created.json()['id']}",
                headers=other_headers,
            ).status_code
            == 404
        )
