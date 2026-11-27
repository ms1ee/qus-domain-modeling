"""Custom exception hierarchy for the Beijing Subway fare calculation system."""


class SubwayError(Exception):
    """Base class for all application-level errors."""


class InputFormatError(SubwayError):
    """Raised when a user query does not follow the 'Start; End' format."""


class UnknownStationError(SubwayError):
    """Raised when a station name cannot be resolved to any known station."""


class LogicError(SubwayError):
    """Raised when a query is logically invalid (e.g. identical start and end)."""


class PathCalculationError(SubwayError):
    """Raised when path calculation fails unexpectedly."""


class FareCalculationError(SubwayError):
    """Raised when fare calculation fails unexpectedly."""
