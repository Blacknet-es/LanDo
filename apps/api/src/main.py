from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
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
from src.application.events.absorb_reminders import AbsorbExternalRemindersUseCase
from src.routers import events, locations, settings, chat, webhooks

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(events.router)
app.include_router(locations.router)
app.include_router(settings.router)
app.include_router(chat.router)
app.include_router(webhooks.router)

@app.get("/", include_in_schema=False)
async def root() -> dict:
    return {"message": "Welcome to LanDo"}