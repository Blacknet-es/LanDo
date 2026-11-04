"""
SQLModel implementation of EventRepository.
"""

from typing import Optional
from sqlmodel import Session, select

from src.application.events.repository import EventRepository
from src.domain.events.entities import Event
from src.infrastructure.db.models import (
    EventModel,
    EventReminderModel,
    RecurrenceRuleModel,
)
from src.infrastructure.db.mapper import (
    event_to_domain,
    event_to_model,
    recurrence_to_model,
    reminder_to_model,
    update_model_from_entity,
)


class SqlModelEventRepository(EventRepository):
    def __init__(self, session: Session) -> None:
        self.session = session

    def find_by_id(self, event_id: str) -> Optional[Event]:
        statement = select(EventModel).where(EventModel.id == event_id)
        model = self.session.exec(statement).first()
        if not model:
            return None
        return event_to_domain(model)

    def find_all(self, limit: int = 100, offset: int = 0) -> list[Event]:
        statement = select(EventModel).offset(offset).limit(limit)
        models = self.session.exec(statement).all()
        return [event_to_domain(m) for m in models]

    def find_by_date_range(
        self, start_date: Optional[object] = None, end_date: Optional[object] = None
    ) -> list[Event]:
        statement = select(EventModel)
        if start_date is not None:
            statement = statement.where(EventModel.start_time >= start_date)
        if end_date is not None:
            statement = statement.where(EventModel.start_time <= end_date)
        statement = statement.order_by(EventModel.start_time)
        models = self.session.exec(statement).all()
        return [event_to_domain(m) for m in models]

    def save(self, event: Event) -> None:
        existing = self.session.get(EventModel, event.id)
        if existing:
            update_model_from_entity(event, existing)
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
            model = event_to_model(event)
            self.session.add(model)
            if event.recurrence_rule:
                rec_model = recurrence_to_model(event.recurrence_rule, event.id)
                self.session.add(rec_model)
            for reminder in event.reminders:
                rem_model = reminder_to_model(reminder, event.id)
                self.session.add(rem_model)

        self.session.commit()

    def delete(self, event_id: str) -> None:
        model = self.session.get(EventModel, event_id)
        if model:
            self.session.delete(model)
            self.session.commit()

