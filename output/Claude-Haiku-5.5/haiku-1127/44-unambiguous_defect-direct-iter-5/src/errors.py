"""Domain-specific exception hierarchy for the Beijing Subway fare system.

Every error that is expected during normal operation derives from
SubwayError, so the command-line layer can catch them in one place and show
a clear, user-friendly message instead of a traceback.
"""


class SubwayError(Exception):
    """Base class for all expected errors raised by the system."""


class DataError(SubwayError):
    """Raised when the subway dataset is missing, unreadable or malformed."""


class DataUpdateError(SubwayError):
    """Raised when a requested data update (add line, modify station, ...) is invalid."""


class InputFormatError(SubwayError):
    """Raised when a user query does not follow the 'Start; End' format."""

    DEFAULT_MESSAGE = (
        "Input format incorrect, please use 'Starting Station; Ending Station' format"
    )

    def __init__(self, message=None):
        super().__init__(message or self.DEFAULT_MESSAGE)


class StationNotFoundError(SubwayError):
    """Raised when a station name cannot be matched to any station in the network."""

    def __init__(self, name, role="Station", suggestions=None):
        self.name = name
        self.role = role
        self.suggestions = list(suggestions or [])
        message = f"{role} '{name}' does not exist, please check the station name"
        if self.suggestions:
            message += f" (did you mean: {', '.join(self.suggestions)}?)"
        super().__init__(message)


class InvalidQueryError(SubwayError):
    """Raised when a syntactically valid query is logically invalid (e.g. same start and end)."""


class PathNotFoundError(SubwayError):
    """Raised when no route exists between two stations under the given constraints."""


class FareCalculationError(SubwayError):
    """Raised when the fare for a computed route cannot be calculated."""
