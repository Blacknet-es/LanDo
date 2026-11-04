"""Health check router."""

from datetime import datetime, timezone

from fastapi import APIRouter

router = APIRouter(prefix="/health", tags=["health"])


@router.get("", summary="Health check")
async def health_check() -> dict:
    """Returns API liveness status and current UTC timestamp."""
    return {
        "status": "ok",
        "service": "lando-api",
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
