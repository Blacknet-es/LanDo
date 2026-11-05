from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import BaseMessage
from langgraph.graph import StateGraph, END
from langgraph.graph.message import add_messages
from langgraph.prebuilt import ToolNode
from langgraph.checkpoint.memory import MemorySaver
from sqlmodel import Session
from typing_extensions import Optional, Literal
from datetime import datetime
from langchain_core.messages import SystemMessage
from src.agent.tools.locations import get_location_tools
from src.application.events.create_event import CreateEventUseCase
from src.application.events.reschedule_event import RescheduleEventUseCase
from src.application.events.repository import EventRepository
from src.application.events.exceptions import ImmutableEventException
from src.application.events.absorb_reminders import AbsorbExternalRemindersUseCase
from src.infrastructure.webhooks.n8n_publisher import publish_webhook

router = APIRouter()

def get_webhook_secret():
    return "your_secret_here"

@router.post("/api/v1/webhooks/location-trigger")
async def location_trigger(
    request: Request,
    user_id: str,
    location_id: str,
    trigger_type: str,
    webhook_secret: str = Depends(get_webhook_secret),
):
    if webhook_secret != os.getenv("WEBHOOK_SECRET"):
        raise HTTPException(status_code=401, detail="Invalid webhook secret")

    # Handle location trigger logic here
    return {"message": "Location trigger received"}

@router.post("/api/v1/webhooks/external-event")
async def external_event(
    request: Request,
    event_data: dict,
    webhook_secret: str = Depends(get_webhook_secret),
):
    if webhook_secret != os.getenv("WEBHOOK_SECRET"):
        raise HTTPException(status_code=401, detail="Invalid webhook secret")

    use_case = AbsorbExternalRemindersUseCase(
        repository=EventRepository(session),
        dispatcher=DomainEventDispatcher(),
    )
    use_case.execute(event_data)

    return {"message": "External event absorbed"}
