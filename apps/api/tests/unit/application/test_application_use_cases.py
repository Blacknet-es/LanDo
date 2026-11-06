"""Unit tests for Application Use Cases and Domain Events."""

from datetime import datetime, timezone, timedelta
from typing import Optional
import pytest

from src.application.events.create_event import CreateEventUseCase
from src.application.events.reschedule_event import RescheduleEventUseCase
from src.application.events.absorb_reminders import AbsorbExternalRemindersUseCase
from src.application.events.dtos import (
    CreateEventCommand,
    RescheduleEventCommand,
    AbsorbExternalRemindersCommand,
    RecurrenceRuleDTO,
)
from src.application.events.repository import EventRepository
from src.infrastructure.events.dispatcher import InMemoryDomainEventDispatcher
from src.domain.events.entities import Event
from src.domain.events.events import (
    EventCreatedDomainEvent,
    EventRescheduledDomainEvent,
    ReminderScheduledDomainEvent,
    ExternalReminderAbsorbedDomainEvent,
)
from src.domain.events.exceptions import ImmutableEventException, EventNotFoundException
from src.domain.events.value_objects import (
    EventSource,
    EnergyLevel,
    DopamineReward,
    RecurrenceFrequency,
)


class InMemoryEventRepository(EventRepository):
    """In-memory stub implementation of EventRepository for fast unit testing."""

    def __init__(self) -> None:
        self.events: dict[str, Event] = {}

    def find_by_id(self, event_id: str) -> Optional[Event]:
        return self.events.get(event_id)

    def save(self, event: Event) -> None:
        self.events[event.id] = event

    def delete(self, event_id: str) -> None:
        self.events.pop(event_id, None)


def _now() -> datetime:
    return datetime.now(timezone.utc)


class TestCreateEventUseCase:
    def test_create_valid_event_persists_and_dispatches_events(self):
        repo = InMemoryEventRepository()
        dispatcher = InMemoryDomainEventDispatcher()
        use_case = CreateEventUseCase(repo, dispatcher)

        cmd = CreateEventCommand(
            title="Design Review",
            start_time=_now(),
            end_time=_now() + timedelta(hours=1),
            description="Discuss architecture",
            energy_level=EnergyLevel.HIGH_ENERGY,
            cognitive_load=4,
            dopamine_reward=DopamineReward.HIGH,
            reminder_minutes=[15, 60],
        )

        event = use_case.execute(cmd)

        # 1. Assert persistence
        assert event.id in repo.events
        assert repo.events[event.id].title == "Design Review"
        assert len(repo.events[event.id].reminders) == 2

        # 2. Assert dispatched domain events
        dispatched_types = [type(e) for e in dispatcher.collected]
        assert EventCreatedDomainEvent in dispatched_types
        # Reminders scheduled events should also be dispatched
        reminder_events = [
            e for e in dispatcher.collected if isinstance(e, ReminderScheduledDomainEvent)
        ]
        assert len(reminder_events) == 2
        assert reminder_events[0].minutes_before == 15
        assert reminder_events[1].minutes_before == 60

    def test_create_event_with_recurrence(self):
        repo = InMemoryEventRepository()
        dispatcher = InMemoryDomainEventDispatcher()
        use_case = CreateEventUseCase(repo, dispatcher)

        cmd = CreateEventCommand(
            title="Daily Standup",
            start_time=_now(),
            recurrence_rule=RecurrenceRuleDTO(
                frequency=RecurrenceFrequency.DAILY,
                interval=1,
                count=10,
            ),
        )

        event = use_case.execute(cmd)
        assert event.recurrence_rule is not None
        assert event.recurrence_rule.frequency == RecurrenceFrequency.DAILY
        assert event.recurrence_rule.count == 10


class TestRescheduleEventUseCase:
    def test_reschedule_local_event_updates_and_dispatches(self):
        repo = InMemoryEventRepository()
        dispatcher = InMemoryDomainEventDispatcher()
        create_uc = CreateEventUseCase(repo, dispatcher)
        reschedule_uc = RescheduleEventUseCase(repo, dispatcher)

        initial_start = _now()
        initial_end = initial_start + timedelta(hours=1)
        event = create_uc.execute(
            CreateEventCommand(
                title="Sprint Planning",
                start_time=initial_start,
                end_time=initial_end,
            )
        )
        dispatcher.clear_collected()

        new_start = initial_start + timedelta(days=1)
        new_end = new_start + timedelta(hours=1)
        reschedule_uc.execute(
            RescheduleEventCommand(
                event_id=event.id,
                new_start_time=new_start,
                new_end_time=new_end,
            )
        )

        # Assert time range updated
        saved = repo.find_by_id(event.id)
        assert saved is not None
        assert saved.time_range.start_time == new_start
        assert saved.time_range.end_time == new_end

        # Assert domain event dispatched
        assert len(dispatcher.collected) == 1
        resched_event = dispatcher.collected[0]
        assert isinstance(resched_event, EventRescheduledDomainEvent)
        assert resched_event.aggregate_id == event.id
        assert resched_event.old_start == initial_start
        assert resched_event.new_start == new_start

    def test_reschedule_read_only_event_blocks_before_persistence(self):
        repo = InMemoryEventRepository()
        dispatcher = InMemoryDomainEventDispatcher()
        create_uc = CreateEventUseCase(repo, dispatcher)
        reschedule_uc = RescheduleEventUseCase(repo, dispatcher)

        initial_start = _now()
        event = create_uc.execute(
            CreateEventCommand(
                title="Google Cal Event",
                start_time=initial_start,
                source=EventSource.GOOGLE_CALENDAR,
            )
        )
        dispatcher.clear_collected()

        with pytest.raises(ImmutableEventException):
            reschedule_uc.execute(
                RescheduleEventCommand(
                    event_id=event.id,
                    new_start_time=initial_start + timedelta(days=2),
                )
            )

        # Assert no persistence mutation
        saved = repo.find_by_id(event.id)
        assert saved.time_range.start_time == initial_start
        # Assert no events dispatched
        assert len(dispatcher.collected) == 0

    def test_reschedule_nonexistent_event_raises_not_found(self):
        repo = InMemoryEventRepository()
        dispatcher = InMemoryDomainEventDispatcher()
        reschedule_uc = RescheduleEventUseCase(repo, dispatcher)

        with pytest.raises(EventNotFoundException):
            reschedule_uc.execute(
                RescheduleEventCommand(
                    event_id="invalid-id",
                    new_start_time=_now(),
                )
            )


class TestAbsorbExternalRemindersUseCase:
    def test_absorb_reminders_on_external_event_dispatches_events(self):
        repo = InMemoryEventRepository()
        dispatcher = InMemoryDomainEventDispatcher()
        create_uc = CreateEventUseCase(repo, dispatcher)
        absorb_uc = AbsorbExternalRemindersUseCase(repo, dispatcher)

        event = create_uc.execute(
            CreateEventCommand(
                title="Synced CalDAV Event",
                start_time=_now(),
                source=EventSource.CALDAV,
            )
        )
        dispatcher.clear_collected()

        absorb_uc.execute(
            AbsorbExternalRemindersCommand(
                event_id=event.id,
                reminder_minutes=[10, 30],
            )
        )

        saved = repo.find_by_id(event.id)
        assert len(saved.reminders) == 2
        assert all(r.is_absorbed_from_external for r in saved.reminders)

        # Assert ExternalReminderAbsorbedDomainEvent dispatched
        absorbed_events = [
            e for e in dispatcher.collected if isinstance(e, ExternalReminderAbsorbedDomainEvent)
        ]
        assert len(absorbed_events) == 2
        assert absorbed_events[0].minutes_before == 10
        assert absorbed_events[0].external_source == "CALDAV"
