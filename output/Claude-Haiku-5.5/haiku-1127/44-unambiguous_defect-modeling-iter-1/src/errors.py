"""Domain-specific exception hierarchy for the Beijing Subway fare system.

All errors that are expected during normal use (bad input, unknown stations,
unreachable destinations, malformed data) derive from ``SubwayError`` so the
CLI can catch them in one place and print a friendly message.
"""


class SubwayError(Exception):
    """Base class for all expected errors raised by the subway system."""


class InputFormatError(SubwayError):
    """Raised when a query string does not follow the 'Start; End' format."""


class ValidationError(SubwayError):
    """Raised when a query is syntactically valid but logically invalid."""


class StationNotFoundError(SubwayError):
    """Raised when a station name cannot be matched to an official station."""

    def __init__(self, role: str, name: str) -> None:
        self.role = role
        self.name = name
        super().__init__(
            f"{role} station '{name}' does not exist, please check the station name"
        )


class PathNotFoundError(SubwayError):
    """Raised when no path exists between two stations under the given constraints."""


class FareError(SubwayError):
    """Raised when a fare or time estimate cannot be computed."""


class DataError(SubwayError):
    """Raised when subway data is missing, malformed, or cannot be updated."""
