"""
Integration tests for /api/locations endpoints and location-based triggers in events.
"""

import pytest
from fastapi.testclient import TestClient
from sqlmodel import SQLModel, Session, create_engine
from sqlmodel.pool import StaticPool

from src.main import app
from src.infrastructure.db.session import get_session
from src.agent.tools.events import get_event_tools
from src.agent.tools.locations import get_location_tools


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
    def get_session_override():
        return session

    app.dependency_overrides[get_session] = get_session_override
    client = TestClient(app)
    yield client
    app.dependency_overrides.clear()


class TestLocationsApiIntegration:
    def test_create_and_get_locations(self, client: TestClient):
        # 1. Create Location
        payload = {
            "name": "Home",
            "latitude": 40.4168,
            "longitude": -3.7038,
            "radius_meters": 100,
        }
        res = client.post("/api/locations", json=payload)
        assert res.status_code == 201
        data = res.json()
        assert data["name"] == "Home"
        assert data["latitude"] == 40.4168
        assert "id" in data

        # 2. Get Locations List
        get_res = client.get("/api/locations")
        assert get_res.status_code == 200
        locs = get_res.json()
        assert len(locs) >= 1
        assert any(l["name"] == "Home" for l in locs)

    def test_create_location_invalid_coords(self, client: TestClient):
        res = client.post(
            "/api/locations",
            json={"name": "Bad", "latitude": 120.0, "longitude": 0.0},
        )
        assert res.status_code == 422

    def test_create_event_with_location_trigger_api(self, client: TestClient):
        # Create location first
        loc_res = client.post(
            "/api/locations",
            json={"name": "Office", "latitude": 40.45, "longitude": -3.69},
        )
        assert loc_res.status_code == 201
        loc_id = loc_res.json()["id"]

        # Create event with LOCATION_ENTER trigger
        event_payload = {
            "title": "Recoger llaves de repuesto",
            "start_time": "2026-11-05T09:00:00Z",
            "trigger_type": "LOCATION_ENTER",
            "location_id": loc_id,
            "trigger_condition": "ON_ENTER",
        }
        event_res = client.post("/events", json=event_payload)
        assert event_res.status_code == 201
        event_data = event_res.json()
        assert event_data["trigger_type"] == "LOCATION_ENTER"
        assert event_data["location_id"] == loc_id
        assert event_data["trigger_condition"] == "ON_ENTER"

    def test_agent_tools_location_trigger_flow(self, session: Session):
        loc_tools = {t.name: t for t in get_location_tools(session)}
        event_tools = {t.name: t for t in get_event_tools(session)}

        # 1. User saves "Casa de mis padres"
        save_res = loc_tools["manage_locations"].invoke({
            "action": "create",
            "name": "Casa de mis padres",
            "latitude": 40.4150,
            "longitude": -3.7000,
            "radius_meters": 120,
        })
        assert save_res["status"] == "success"

        # 2. User schedules contextual reminder when arriving at "Casa de mis padres"
        remind_res = event_tools["create_event"].invoke({
            "title": "Pedir el libro prestado",
            "start_time": "2026-11-05T18:00:00Z",
            "trigger_type": "LOCATION",
            "location_name": "Casa de mis padres",
            "trigger_condition": "ENTER",
        })
        assert remind_res["status"] == "success"
        assert remind_res["trigger_type"] == "LOCATION_ENTER"
        assert "location_id" in remind_res

        # 3. Target unknown location -> friendly error prompting to save place
        bad_remind = event_tools["create_event"].invoke({
            "title": "Hacer algo",
            "start_time": "2026-11-05T18:00:00Z",
            "trigger_type": "LOCATION",
            "location_name": "Sitio Desconocido",
        })
        assert "error" in bad_remind
        assert "not found in saved places" in bad_remind["error"]
