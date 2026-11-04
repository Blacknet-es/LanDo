"""
SQLModel persistence schemas for the LanDo event bounded context.

Design notes:
- TimeRange is flattened to ``start_time`` / ``end_time`` columns (no nested JSON).
- Enum values are stored as plain VARCHAR strings for readability and
  portability (no Postgres ENUM types that require migrations to extend).
- ``RecurrenceRuleModel`` is 1-to-1 with EventModel via a unique FK.
- ``EventReminderModel`` is 1-to-many with EventModel.
- Relationships are lazy by default; use explicit joins in queries.

A separate ``mapper.py`` converts between these SQLModel schemas and the
pure-Python domain entities.
"""

import uuid
from datetime import datetime, timezone
from typing import Optional, List

from sqlmodel import Field, Relationship, SQLModel


def _uuid() -> str:
    return str(uuid.uuid4())


def _now() -> datetime:
    return datetime.now(timezone.utc)


# ── Typology ──────────────────────────────────────────────────────────────────


class TypologyModel(SQLModel, table=True):
    __tablename__ = "typologies"

    id: str = Field(default_factory=_uuid, primary_key=True)
    name: str = Field(index=True, max_length=120)
    color_hex: str = Field(default="#6366f1", max_length=7)
    icon: str = Field(default="📌", max_length=8)
    is_system_preset: bool = Field(default=False)
    created_at: datetime = Field(default_factory=_now)
    updated_at: datetime = Field(default_factory=_now)

    # Back-reference
    events: List["EventModel"] = Relationship(back_populates="typology")


# ── Recurrence Rule (1-to-1 with Event) ───────────────────────────────────────


class RecurrenceRuleModel(SQLModel, table=True):
    __tablename__ = "recurrence_rules"

    id: str = Field(default_factory=_uuid, primary_key=True)
    event_id: str = Field(
        foreign_key="events.id", unique=True, index=True, ondelete="CASCADE"
    )
    # Stored as VARCHAR; maps to RecurrenceFrequency enum values
    frequency: str = Field(max_length=16)
    interval: int = Field(default=1)
    until_date: Optional[datetime] = Field(default=None)
    count: Optional[int] = Field(default=None)

    event: Optional["EventModel"] = Relationship(back_populates="recurrence_rule")


# ── Event Reminder (1-to-many with Event) ─────────────────────────────────────


class EventReminderModel(SQLModel, table=True):
    __tablename__ = "event_reminders"

    id: str = Field(default_factory=_uuid, primary_key=True)
    event_id: str = Field(foreign_key="events.id", index=True, ondelete="CASCADE")
    minutes_before: int
    is_absorbed_from_external: bool = Field(default=False)
    # Stored as VARCHAR; maps to ReminderStatus enum values
    status: str = Field(default="PENDING", max_length=16)
    created_at: datetime = Field(default_factory=_now)

    event: Optional["EventModel"] = Relationship(back_populates="reminders")


# ── Event ─────────────────────────────────────────────────────────────────────


class EventModel(SQLModel, table=True):
    __tablename__ = "events"

    id: str = Field(default_factory=_uuid, primary_key=True)
    title: str = Field(index=True, max_length=255)
    description: Optional[str] = Field(default=None)

    # TimeRange — flattened columns
    start_time: datetime = Field(index=True)
    end_time: Optional[datetime] = Field(default=None)
    is_all_day: bool = Field(default=False)

    # Provenance — stored as VARCHAR enum strings
    source: str = Field(default="LOCAL", max_length=32)
    external_id: Optional[str] = Field(default=None, index=True, max_length=255)
    is_read_only: bool = Field(default=False)

    # Typology FK (nullable — event may be untyped)
    typology_id: Optional[str] = Field(
        default=None, foreign_key="typologies.id", index=True
    )

    # ADHD / Cognitive load attributes — stored as VARCHAR enum strings
    energy_level: str = Field(default="MEDIUM_ENERGY", max_length=32)
    cognitive_load: int = Field(default=3)
    dopamine_reward: str = Field(default="MEDIUM", max_length=16)

    # Audit timestamps
    created_at: datetime = Field(default_factory=_now)
    updated_at: datetime = Field(default_factory=_now)

    # Relationships
    typology: Optional[TypologyModel] = Relationship(back_populates="events")
    recurrence_rule: Optional[RecurrenceRuleModel] = Relationship(
        back_populates="event"
    )
    reminders: List[EventReminderModel] = Relationship(back_populates="event")

