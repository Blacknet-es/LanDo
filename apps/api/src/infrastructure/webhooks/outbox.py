import logging
from collections.abc import Callable
from datetime import UTC, datetime, timedelta
from typing import Any

from sqlmodel import Session, select

from src.infrastructure.db.models import EventOutboxModel
from src.infrastructure.webhooks.n8n_publisher import publish_webhook

logger = logging.getLogger(__name__)
WebhookPublisher = Callable[[str, dict[str, Any]], None]


def deliver_pending_events(
    session: Session,
    publisher: WebhookPublisher = publish_webhook,
    batch_size: int = 25,
    now: datetime | None = None,
) -> int:
    current_time = now or datetime.now(UTC)
    statement = (
        select(EventOutboxModel)
        .where(
            EventOutboxModel.delivered_at.is_(None),
            EventOutboxModel.next_attempt_at <= current_time,
        )
        .order_by(EventOutboxModel.created_at)
        .limit(batch_size)
        .with_for_update(skip_locked=True)
    )
    pending = session.exec(statement).all()

    delivered = 0
    for event in pending:
        try:
            publisher(event.event_type, event.payload)
        except Exception as exc:
            event.attempts += 1
            delay_seconds = min(2 ** min(event.attempts, 12), 3600)
            event.next_attempt_at = current_time + timedelta(seconds=delay_seconds)
            event.last_error = str(exc)[:2000]
            logger.exception(
                "n8n event delivery failed for outbox event %s; retry %s scheduled",
                event.event_id,
                event.attempts,
            )
        else:
            event.delivered_at = current_time
            event.last_error = None
            delivered += 1
        session.add(event)
        session.commit()
    return delivered
