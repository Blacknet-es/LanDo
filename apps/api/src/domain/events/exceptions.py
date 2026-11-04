"""
Domain exceptions for the LanDo event bounded context.
All exceptions inherit from LandoDomainException for uniform catching at application boundaries.
"""


class LandoDomainException(Exception):
    """Base class for all LanDo domain exceptions."""


class ImmutableEventException(LandoDomainException):
    """
    Raised when a mutation is attempted on a read-only event.

    Events originating from external sources (Google Calendar, CalDAV, etc.)
    are marked read-only on absorption. All structural mutations must be
    performed in the source system, not in LanDo.
    """

    def __init__(self, event_id: str, source: str) -> None:
        super().__init__(
            f"Event '{event_id}' is read-only because it originates from '{source}'. "
            "Mutate the event in its source system instead."
        )
        self.event_id = event_id
        self.source = source


class InvalidCognitiveLoadException(LandoDomainException):
    """Raised when cognitive_load is set outside the valid range [1, 5]."""

    def __init__(self, value: int) -> None:
        super().__init__(f"cognitive_load must be an integer between 1 and 5, got {value!r}.")
        self.value = value


class InvalidRecurrenceRuleException(LandoDomainException):
    """Raised when a RecurrenceRule is constructed with contradictory constraints."""


class EventNotFoundException(LandoDomainException):
    """Raised by use-cases when a requested event does not exist in the repository."""

    def __init__(self, event_id: str) -> None:
        super().__init__(f"Event with id '{event_id}' was not found.")
        self.event_id = event_id

