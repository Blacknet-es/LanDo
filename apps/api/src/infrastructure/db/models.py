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
from datetime import UTC, datetime
from typing import Any, Optional
from uuid import UUID, uuid4

from pgvector.sqlalchemy import Vector
from sqlalchemy import CheckConstraint, Column, ForeignKeyConstraint, Text, UniqueConstraint
from sqlalchemy.ext.compiler import compiles
from sqlmodel import JSON, Field, Relationship, SQLModel


def _uuid() -> str:
    return str(uuid.uuid4())


def _now() -> datetime:
    return datetime.now(UTC)


class UserModel(SQLModel, table=True):
    __tablename__ = "users"
    __table_args__ = (
        CheckConstraint(
            "preferred_language IN ('es', 'en')",
            name="ck_users_preferred_language",
        ),
    )

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    email: str = Field(unique=True, index=True, max_length=320)
    hashed_password: str = Field(max_length=255)
    preferred_language: str = Field(default="es", max_length=5)
    created_at: datetime = Field(default_factory=_now)


class UserLocationModel(SQLModel, table=True):
    __tablename__ = "user_locations"
    __table_args__ = (UniqueConstraint("id", "user_id", name="uq_user_locations_id_user"),)

    id: str = Field(default_factory=_uuid, primary_key=True)
    user_id: UUID = Field(foreign_key="users.id", index=True)
    name: str = Field(index=True, max_length=120)
    latitude: float
    longitude: float
    radius_meters: int = Field(default=100)
    created_at: datetime = Field(default_factory=_now)
    updated_at: datetime = Field(default_factory=_now)


class LocationTriggerModel(SQLModel, table=True):
    __tablename__ = "location_triggers"
    __table_args__ = (
        ForeignKeyConstraint(
            ["location_id", "user_id"],
            ["user_locations.id", "user_locations.user_id"],
            name="fk_location_triggers_location_tenant",
        ),
    )

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    user_id: UUID = Field(foreign_key="users.id", index=True)
    location_id: str = Field(index=True)
    trigger_type: str = Field(max_length=32)
    created_at: datetime = Field(default_factory=_now)


class UserSettingsModel(SQLModel, table=True):
    __tablename__ = "user_settings"

    id: str = Field(default_factory=_uuid, primary_key=True)
    user_id: UUID = Field(foreign_key="users.id", unique=True, index=True)
    selected_provider: str = Field(default="ollama")
    selected_model: str = Field(default="qwen2.5:7b")
    api_keys: dict[str, str] = Field(default_factory=dict, sa_type=JSON)
    ollama_base_url: str = Field(default="http://host.docker.internal:11434")
    created_at: datetime = Field(default_factory=_now)
    updated_at: datetime = Field(default_factory=_now)


@compiles(Vector, "sqlite")
def _compile_vector_for_sqlite(_type: Vector, _compiler: object, **_kwargs: object) -> str:
    return "TEXT"


class MemoryItemModel(SQLModel, table=True):
    __tablename__ = "memory_items"

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    user_id: UUID = Field(foreign_key="users.id", index=True)
    content: str = Field(sa_column=Column(Text, nullable=False))
    embedding: list[float] = Field(sa_column=Column(Vector(), nullable=False))
    created_at: datetime = Field(default_factory=_now)


class EventOutboxModel(SQLModel, table=True):
    __tablename__ = "event_outbox"

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    event_id: UUID = Field(unique=True, index=True)
    user_id: UUID = Field(foreign_key="users.id", index=True)
    event_type: str = Field(max_length=100, index=True)
    payload: dict[str, Any] = Field(default_factory=dict, sa_type=JSON)
    attempts: int = Field(default=0)
    next_attempt_at: datetime = Field(default_factory=_now, index=True)
    created_at: datetime = Field(default_factory=_now)
    delivered_at: datetime | None = Field(default=None)
    last_error: str | None = Field(default=None, sa_type=Text)


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
    events: list["EventModel"] = Relationship(back_populates="typology")


# ── Recurrence Rule (1-to-1 with Event) ───────────────────────────────────────


class RecurrenceRuleModel(SQLModel, table=True):
    __tablename__ = "recurrence_rules"

    id: str = Field(default_factory=_uuid, primary_key=True)
    event_id: str = Field(foreign_key="events.id", unique=True, index=True, ondelete="CASCADE")
    # Stored as VARCHAR; maps to RecurrenceFrequency enum values
    frequency: str = Field(max_length=16)
    interval: int = Field(default=1)
    until_date: datetime | None = Field(default=None)
    count: int | None = Field(default=None)

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
    __table_args__ = (
        ForeignKeyConstraint(
            ["location_id", "user_id"],
            ["user_locations.id", "user_locations.user_id"],
            name="fk_events_location_tenant",
        ),
    )

    id: str = Field(default_factory=_uuid, primary_key=True)
    user_id: UUID = Field(foreign_key="users.id", index=True)
    title: str = Field(index=True, max_length=255)
    description: str | None = Field(default=None)

    # TimeRange — flattened columns
    start_time: datetime = Field(index=True)
    end_time: datetime | None = Field(default=None)
    is_all_day: bool = Field(default=False)

    # Provenance — stored as VARCHAR enum strings
    source: str = Field(default="LOCAL", max_length=32)
    external_id: str | None = Field(default=None, index=True, max_length=255)
    is_read_only: bool = Field(default=False)

    # Typology FK (nullable — event may be untyped)
    typology_id: str | None = Field(default=None, foreign_key="typologies.id", index=True)

    # Location & Geofencing triggers
    trigger_type: str = Field(default="TIME_BASED", max_length=32)
    location_id: str | None = Field(default=None, index=True)
    trigger_condition: str | None = Field(default=None, max_length=16)

    # ADHD / Cognitive load attributes — stored as VARCHAR enum strings
    energy_level: str = Field(default="MEDIUM_ENERGY", max_length=32)
    cognitive_load: int = Field(default=3)
    dopamine_reward: str = Field(default="MEDIUM", max_length=16)

    # Audit timestamps
    created_at: datetime = Field(default_factory=_now)
    updated_at: datetime = Field(default_factory=_now)

    # Relationships
    user: UserModel = Relationship()
    typology: TypologyModel | None = Relationship(back_populates="events")
    recurrence_rule: RecurrenceRuleModel | None = Relationship(back_populates="event")
    reminders: list[EventReminderModel] = Relationship(back_populates="event")
