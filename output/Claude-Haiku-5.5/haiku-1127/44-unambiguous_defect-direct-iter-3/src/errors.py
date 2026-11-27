"""Custom exception types shared by the Beijing Subway fare system."""

from __future__ import annotations

INPUT_FORMAT_MESSAGE = (
    "Input format incorrect, please use 'Starting Station; Ending Station' format"
)


class SubwayError(Exception):
    """Base class for all application-specific errors."""


class DataError(SubwayError):
    """Raised when the subway data set is malformed or an update is invalid."""


class StationNotFoundError(SubwayError):
    """Raised when a station name does not match any official station."""

    def __init__(self, name: str, role: str = "Target") -> None:
        self.name = name
        self.role = role
        super().__init__(
            f"{role} station '{name}' does not exist, please check the station name"
        )


class PathNotFoundError(SubwayError):
    """Raised when no route exists between two stations under the given settings."""


class InputFormatError(SubwayError):
    """Raised when a user query does not follow the expected input format."""

    def __init__(self, message: str = INPUT_FORMAT_MESSAGE) -> None:
        super().__init__(message)


class QueryError(SubwayError):
    """Raised for logically invalid queries (e.g. identical start and end)."""
