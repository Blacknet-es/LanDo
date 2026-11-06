import logging
from typing import Any

import httpx

from src.config import settings

logger = logging.getLogger(__name__)


def publish_webhook(event_type: str, event_data: dict[str, Any]) -> None:
    if not settings.n8n_webhook_url:
        raise RuntimeError("N8N webhook URL is not configured")

    headers = {}
    if settings.webhook_secret:
        headers["X-LanDo-Webhook-Secret"] = settings.webhook_secret
    event_id = event_data.get("event_id")
    if isinstance(event_id, str):
        headers["Idempotency-Key"] = event_id
    response = httpx.post(
        settings.n8n_webhook_url,
        json={"event_type": event_type, "event_data": event_data},
        headers=headers,
        timeout=10.0,
    )
    response.raise_for_status()
