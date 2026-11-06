"""
SQLModel implementation of EventRepository.
"""

from datetime import datetime
from uuid import UUID

from sqlmodel import Session, select

from src.application.events.repository import EventRepository
from src.domain.events.entities import Event
from src.infrastructure.db.mapper import (
    event_to_domain,
    event_to_model,
    recurrence_to_model,
    reminder_to_model,
    update_model_from_entity,
)
from src.infrastructure.db.models import EventModel, UserLocationModel


class SqlModelEventRepository(EventRepository):
    def __init__(self, session: Session, user_id: UUID) -> None:
        self.session = session
        self.user_id = user_id

    def find_by_id(self, event_id: str) -> Event | None:
        statement = select(EventModel).where(
            EventModel.id == event_id,
            EventModel.user_id == self.user_id,
        )
        model = self.session.exec(statement).first()
        if not model:
            return None
        return event_to_domain(model)

    def find_all(self, limit: int = 100, offset: int = 0) -> list[Event]:
        statement = (
            select(EventModel).where(EventModel.user_id == self.user_id).offset(offset).limit(limit)
        )
        models = self.session.exec(statement).all()
        return [event_to_domain(m) for m in models]

    def find_by_date_range(
        self, start_date: datetime | None = None, end_date: datetime | None = None
    ) -> list[Event]:
        statement = select(EventModel).where(EventModel.user_id == self.user_id)
        if start_date is not None:
            statement = statement.where(EventModel.start_time >= start_date)
        if end_date is not None:
            statement = statement.where(EventModel.start_time <= end_date)
        statement = statement.order_by(EventModel.start_time)
        models = self.session.exec(statement).all()
        return [event_to_domain(m) for m in models]

    def save(self, event: Event) -> None:
        if event.location_id is not None:
            location = self.session.exec(
                select(UserLocationModel).where(
                    UserLocationModel.id == event.location_id,
                    UserLocationModel.user_id == self.user_id,
                )
            ).first()
            if location is None:
                raise ValueError("Location not found for this user.")

        existing = self.session.exec(
            select(EventModel).where(
                EventModel.id == event.id,
                EventModel.user_id == self.user_id,
            )
        ).first()
        if existing:
            update_model_from_entity(event, existing, self.user_id)
            # Remove old related models and re-add (or sync)
            if existing.recurrence_rule:
                self.session.delete(existing.recurrence_rule)
            if event.recurrence_rule:
                rec_model = recurrence_to_model(event.recurrence_rule, event.id)
                self.session.add(rec_model)

            for rem in existing.reminders:
                self.session.delete(rem)
            for reminder in event.reminders:
                rem_model = reminder_to_model(reminder, event.id)
                self.session.add(rem_model)

            self.session.add(existing)
        else:
            model = event_to_model(event, self.user_id)
            self.session.add(model)
            if event.recurrence_rule:
                rec_model = recurrence_to_model(event.recurrence_rule, event.id)
                self.session.add(rec_model)
            for reminder in event.reminders:
                rem_model = reminder_to_model(reminder, event.id)
                self.session.add(rem_model)

        self.session.flush()

    def delete(self, event_id: str) -> None:
        model = self.session.exec(
            select(EventModel).where(
                EventModel.id == event_id,
                EventModel.user_id == self.user_id,
            )
        ).first()
        if model:
            self.session.delete(model)
            self.session.flush()
