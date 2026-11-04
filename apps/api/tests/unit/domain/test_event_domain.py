"""Unit tests for Event Domain entities, value objects, and invariants."""

from datetime import datetime, timezone, timedelta
import pytest

from src.domain.events.entities import Event, Typology
from src.domain.events.exceptions import (
    ImmutableEventException,
    InvalidCognitiveLoadException,
)
from src.domain.events.value_objects import (
    DopamineReward,
    EnergyLevel,
    EventReminder,
    EventSource,
    RecurrenceFrequency,
    RecurrenceRule,
    ReminderStatus,
    TimeRange,
)


def _now() -> datetime:
    return datetime.now(timezone.utc)


class TestEventInvariantsAndImmutability:
    def test_local_event_is_mutable_by_default(self):
        time_range = TimeRange(start_time=_now(), end_time=_now() + timedelta(hours=1))
        event = Event.create(title="Local Meeting", time_range=time_range)

        assert event.is_read_only is False
        assert event.source == EventSource.LOCAL

        # Should be able to reschedule
        new_range = TimeRange(start_time=_now() + timedelta(hours=2))
        event.reschedule(new_range)
        assert event.time_range == new_range

        # Should be able to update details
        event.update_details(title="Updated Title")
        assert event.title == "Updated Title"

    def test_external_source_must_be_read_only_or_raises_error(self):
        time_range = TimeRange(start_time=_now())
        # Direct constructor check
        with pytest.raises(ValueError, match="must have is_read_only=True"):
            Event(
                title="Synced Event",
                time_range=time_range,
                source=EventSource.GOOGLE_CALENDAR,
                is_read_only=False,
            )

    def test_external_event_via_factory_is_read_only(self):
        time_range = TimeRange(start_time=_now())
        event = Event.create(
            title="Google Cal Event",
            time_range=time_range,
            source=EventSource.GOOGLE_CALENDAR,
        )
        assert event.is_read_only is True
        assert event.source == EventSource.GOOGLE_CALENDAR

    def test_immutable_event_exception_on_reschedule(self):
        time_range = TimeRange(start_time=_now())
        event = Event.create(
            title="Caldav Event",
            time_range=time_range,
            source=EventSource.CALDAV,
        )
        new_range = TimeRange(start_time=_now() + timedelta(days=1))

        with pytest.raises(ImmutableEventException) as exc_info:
            event.reschedule(new_range)

        assert exc_info.value.source == "CALDAV"
        assert exc_info.value.event_id == event.id

    def test_immutable_event_exception_on_update_details(self):
        time_range = TimeRange(start_time=_now())
        event = Event.create(
            title="Google Event",
            time_range=time_range,
            source=EventSource.GOOGLE_CALENDAR,
        )

        with pytest.raises(ImmutableEventException):
            event.update_details(title="Changed Title")

    def test_immutable_event_exception_on_add_reminder(self):
        time_range = TimeRange(start_time=_now())
        event = Event.create(
            title="Google Event",
            time_range=time_range,
            source=EventSource.GOOGLE_CALENDAR,
        )

        with pytest.raises(ImmutableEventException):
            event.add_reminder(15)

    def test_immutable_event_allows_absorbing_external_reminders(self):
        time_range = TimeRange(start_time=_now())
        event = Event.create(
            title="External Synced",
            time_range=time_range,
            source=EventSource.GOOGLE_CALENDAR,
        )

        reminder = event.absorb_external_reminder(10)
        assert reminder.minutes_before == 10
        assert reminder.is_absorbed_from_external is True
        assert len(event.reminders) == 1


class TestADHDCognitiveLoadAttributes:
    def test_default_adhd_attributes(self):
        time_range = TimeRange(start_time=_now())
        event = Event.create(title="Brain Task", time_range=time_range)

        assert event.energy_level == EnergyLevel.MEDIUM_ENERGY
        assert event.cognitive_load == 3
        assert event.dopamine_reward == DopamineReward.MEDIUM

    @pytest.mark.parametrize("load", [1, 2, 3, 4, 5])
    def test_valid_cognitive_load_bounds(self, load):
        time_range = TimeRange(start_time=_now())
        event = Event.create(title="Task", time_range=time_range, cognitive_load=load)
        assert event.cognitive_load == load

    @pytest.mark.parametrize("invalid_load", [0, -1, 6, 10])
    def test_invalid_cognitive_load_raises_exception(self, invalid_load):
        time_range = TimeRange(start_time=_now())
        with pytest.raises(InvalidCognitiveLoadException):
            Event.create(title="Task", time_range=time_range, cognitive_load=invalid_load)

    def test_update_cognitive_load_in_bounds(self):
        time_range = TimeRange(start_time=_now())
        event = Event.create(title="Task", time_range=time_range)
        event.update_details(
            energy_level=EnergyLevel.HIGH_ENERGY,
            cognitive_load=5,
            dopamine_reward=DopamineReward.HIGH,
        )
        assert event.energy_level == EnergyLevel.HIGH_ENERGY
        assert event.cognitive_load == 5
        assert event.dopamine_reward == DopamineReward.HIGH

    def test_update_cognitive_load_out_of_bounds_raises(self):
        time_range = TimeRange(start_time=_now())
        event = Event.create(title="Task", time_range=time_range)
        with pytest.raises(InvalidCognitiveLoadException):
            event.update_details(cognitive_load=7)


class TestRecurrenceRule:
    def test_recurrence_rule_invariants(self):
        with pytest.raises(ValueError, match="interval must be ≥ 1"):
            RecurrenceRule(frequency=RecurrenceFrequency.DAILY, interval=0)

        with pytest.raises(ValueError, match="Cannot specify both until_date and count"):
            RecurrenceRule(
                frequency=RecurrenceFrequency.WEEKLY,
                count=5,
                until_date=_now(),
            )

    def test_daily_recurrence_occurrences(self):
        start = datetime(2026, 1, 1, 10, 0, tzinfo=timezone.utc)
        rule = RecurrenceRule(frequency=RecurrenceFrequency.DAILY, interval=1, count=3)

        dates = rule.generate_occurrences(start)
        assert len(dates) == 3
        assert dates[0] == datetime(2026, 1, 1, 10, 0, tzinfo=timezone.utc)
        assert dates[1] == datetime(2026, 1, 2, 10, 0, tzinfo=timezone.utc)
        assert dates[2] == datetime(2026, 1, 3, 10, 0, tzinfo=timezone.utc)

    def test_weekly_recurrence_occurrences(self):
        start = datetime(2026, 1, 1, 9, 0, tzinfo=timezone.utc)
        rule = RecurrenceRule(frequency=RecurrenceFrequency.WEEKLY, interval=2, count=3)

        dates = rule.generate_occurrences(start)
        assert len(dates) == 3
        assert dates[0] == datetime(2026, 1, 1, 9, 0, tzinfo=timezone.utc)
        assert dates[1] == datetime(2026, 1, 15, 9, 0, tzinfo=timezone.utc)
        assert dates[2] == datetime(2026, 1, 29, 9, 0, tzinfo=timezone.utc)

    def test_monthly_recurrence_occurrences(self):
        start = datetime(2026, 1, 31, 14, 0, tzinfo=timezone.utc)
        rule = RecurrenceRule(frequency=RecurrenceFrequency.MONTHLY, interval=1, count=3)

        dates = rule.generate_occurrences(start)
        assert len(dates) == 3
        assert dates[0] == datetime(2026, 1, 31, 14, 0, tzinfo=timezone.utc)
        # February 2026 has 28 days
        assert dates[1] == datetime(2026, 2, 28, 14, 0, tzinfo=timezone.utc)
        assert dates[2] == datetime(2026, 3, 31, 14, 0, tzinfo=timezone.utc)

    def test_until_date_limits_occurrences(self):
        start = datetime(2026, 1, 1, 10, 0, tzinfo=timezone.utc)
        until = datetime(2026, 1, 4, 12, 0, tzinfo=timezone.utc)
        rule = RecurrenceRule(
            frequency=RecurrenceFrequency.DAILY,
            interval=1,
            until_date=until,
        )

        dates = rule.generate_occurrences(start)
        assert len(dates) == 4
        assert dates[-1] == datetime(2026, 1, 4, 10, 0, tzinfo=timezone.utc)


class TestEventReminder:
    def test_reminder_creation_and_defaults(self):
        reminder = EventReminder(minutes_before=30)
        assert reminder.minutes_before == 30
        assert reminder.is_absorbed_from_external is False
        assert reminder.status == ReminderStatus.PENDING
        assert reminder.is_pending is True

    def test_reminder_negative_minutes_raises_error(self):
        with pytest.raises(ValueError, match="must be non-negative"):
            EventReminder(minutes_before=-5)

    def test_reminder_dispatch_transition(self):
        reminder = EventReminder(minutes_before=15)
        dispatched = reminder.dispatch()

        # Check immutability
        assert reminder.status == ReminderStatus.PENDING
        assert dispatched.status == ReminderStatus.DISPATCHED
        assert dispatched.is_pending is False
        assert dispatched.minutes_before == 15

    def test_absorbed_reminder_flags(self):
        reminder = EventReminder(minutes_before=60, is_absorbed_from_external=True)
        assert reminder.is_absorbed_from_external is True
        assert reminder.status == ReminderStatus.PENDING

