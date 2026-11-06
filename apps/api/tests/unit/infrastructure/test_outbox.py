from datetime import UTC, datetime, timedelta
from uuid import uuid4

from sqlmodel import Session, SQLModel, create_engine, select
from sqlmodel.pool import StaticPool

from src.infrastructure.db.models import EventOutboxModel, UserModel
from src.infrastructure.webhooks.outbox import deliver_pending_events


def test_outbox_retries_failed_delivery_then_marks_event_delivered() -> None:
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    SQLModel.metadata.create_all(engine)
    now = datetime.now(UTC)
    user = UserModel(email="outbox@example.com", hashed_password="unused")
    event = EventOutboxModel(
        user_id=user.id,
        event_id=uuid4(),
        event_type="event.created",
        payload={"event_id": "event-1"},
        next_attempt_at=now,
        created_at=now,
    )
    with Session(engine) as session:
        session.add(user)
        session.add(event)
        session.commit()

        def fail_delivery(_event_type: str, _payload: dict) -> None:
            raise RuntimeError("n8n unavailable")

        assert deliver_pending_events(session, fail_delivery, now=now) == 0
        session.refresh(event)
        assert event.attempts == 1
        assert event.last_error == "n8n unavailable"
        assert event.next_attempt_at == now + timedelta(seconds=2)

        delivered_payloads: list[dict] = []
        assert (
            deliver_pending_events(
                session,
                lambda _event_type, payload: delivered_payloads.append(payload),
                now=event.next_attempt_at,
            )
            == 1
        )
        session.refresh(event)
        assert event.delivered_at == event.next_attempt_at
        assert event.last_error is None
        assert delivered_payloads == [{"event_id": "event-1"}]
        assert len(session.exec(select(EventOutboxModel)).all()) == 1
    SQLModel.metadata.drop_all(engine)
