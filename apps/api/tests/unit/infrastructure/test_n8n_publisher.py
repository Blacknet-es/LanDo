from unittest.mock import Mock

from src.config import settings
from src.infrastructure.webhooks.n8n_publisher import publish_webhook


def test_publisher_sends_secret_and_idempotency_headers(monkeypatch) -> None:
    response = Mock()
    request = Mock(return_value=response)
    monkeypatch.setattr("src.infrastructure.webhooks.n8n_publisher.httpx.post", request)
    monkeypatch.setattr(settings, "n8n_webhook_url", "http://n8n.test/webhook/events")
    monkeypatch.setattr(settings, "webhook_secret", "trusted-secret")

    publish_webhook("event.created", {"event_id": "event-uuid"})

    request.assert_called_once_with(
        "http://n8n.test/webhook/events",
        json={"event_type": "event.created", "event_data": {"event_id": "event-uuid"}},
        headers={
            "X-LanDo-Webhook-Secret": "trusted-secret",
            "Idempotency-Key": "event-uuid",
        },
        timeout=10.0,
    )
    response.raise_for_status.assert_called_once_with()
