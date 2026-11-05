import requests
from typing import List, Dict
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

def publish_webhook(event_type: str, event_data: Dict):
    n8n_webhook_url = os.getenv("N8N_WEBHOOK_URL")
    if not n8n_webhook_url:
        raise Exception("N8N webhook URL not configured")

    response = requests.post(n8n_webhook_url, json={"event_type": event_type, "event_data": event_data})
    response.raise_for_status()
