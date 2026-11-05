"""
Domain exceptions for locations context.
"""

from src.domain.events.exceptions import LandoDomainException


class LocationNotFoundException(LandoDomainException):
    """Raised when a requested user location cannot be found."""

    def __init__(self, identifier: str) -> None:
        super().__init__(f"User location '{identifier}' was not found.")
        self.identifier = identifier


class InvalidCoordinatesException(LandoDomainException):
    """Raised when latitude or longitude are outside valid geographic bounds."""

    def __init__(self, lat: float, lon: float) -> None:
        super().__init__(f"Invalid coordinates: latitude={lat} (must be -90..90), longitude={lon} (must be -180..180).")
        self.lat = lat
        self.lon = lon

