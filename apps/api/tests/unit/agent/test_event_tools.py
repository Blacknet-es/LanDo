"""
Unit tests for LangChain event tools.
"""

from datetime import datetime, timedelta, timezone

import pytest
from sqlmodel import Session, SQLModel, create_engine
from sqlmodel.pool import StaticPool

from src.agent.tools.events import get_event_tools
from src.domain.events.entities import Event
from src.domain.events.value_objects import EventSource, TimeRange
from src.infrastructure.db.repositories import SqlModelEventRepository
from tests.auth_utils import create_test_user, get_test_user_id


@pytest.fixture(name="session")
def session_fixture():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    SQLModel.metadata.create_all(engine)
    with Session(engine) as session:
        create_test_user(session, "event-tools@example.com")
        yield session
    SQLModel.metadata.drop_all(engine)


class TestEventTools:
    def test_create_event_tool_success(self, session: Session):
        tools = {t.name: t for t in get_event_tools(session, get_test_user_id(session))}
        assert "create_event" in tools

        res = tools["create_event"].invoke(
            {
                "title": "Gym Workout",
                "start_time": "2026-11-05T08:00:00Z",
                "end_time": "2026-11-05T09:00:00Z",
                "energy_level": "HIGH_ENERGY",
                "cognitive_load": 2,
            }
        )

        assert res["status"] == "success"
        assert res["title"] == "Gym Workout"
        assert res["energy_level"] == "HIGH_ENERGY"
        assert res["cognitive_load"] == 2
        assert "event_id" in res

    def test_get_events_tool_filtering(self, session: Session):
        tools = {t.name: t for t in get_event_tools(session, get_test_user_id(session))}

        # Create two events
        tools["create_event"].invoke(
            {
                "title": "Event 1",
                "start_time": "2026-11-05T10:00:00Z",
            }
        )
        tools["create_event"].invoke(
            {
                "title": "Event 2",
                "start_time": "2026-11-10T10:00:00Z",
            }
        )

        # Query all
        res_all = tools["get_events"].invoke({})
        assert res_all["count"] == 2

        # Filter date range
        res_filtered = tools["get_events"].invoke(
            {
                "start_date": "2026-11-05T00:00:00Z",
                "end_date": "2026-11-06T00:00:00Z",
            }
        )
        assert res_filtered["count"] == 1
        assert res_filtered["events"][0]["title"] == "Event 1"

    def test_reschedule_event_tool_success(self, session: Session):
        tools = {t.name: t for t in get_event_tools(session, get_test_user_id(session))}
        created = tools["create_event"].invoke(
            {
                "title": "Dentist",
                "start_time": "2026-11-05T12:00:00Z",
            }
        )
        event_id = created["event_id"]

        res = tools["reschedule_event"].invoke(
            {
                "event_id": event_id,
                "new_start_time": "2026-11-06T14:00:00Z",
            }
        )
        assert res["status"] == "success"

        # Verify
        events = tools["get_events"].invoke({"start_date": "2026-11-06T00:00:00Z"})
        assert events["count"] == 1
        assert "2026-11-06T14:00:00" in events["events"][0]["start_time"]

    def test_reschedule_read_only_event_returns_error(self, session: Session):
        user_id = get_test_user_id(session)
        repo = SqlModelEventRepository(session, user_id)
        # Manually create external event (is_read_only=True)
        now = datetime.now(timezone.utc)
        ext_event = Event.create(
            title="Google Calendar Event",
            time_range=TimeRange(start_time=now),
            source=EventSource.GOOGLE_CALENDAR,
        )
        repo.save(ext_event)

        tools = {t.name: t for t in get_event_tools(session, user_id)}
        res = tools["reschedule_event"].invoke(
            {
                "event_id": ext_event.id,
                "new_start_time": (now + timedelta(days=1)).isoformat(),
            }
        )

        assert "error" in res
        assert "cannot be modified because it is read-only" in res["error"]
