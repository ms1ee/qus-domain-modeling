"""Custom exception hierarchy for the Beijing Subway fare calculation system."""


class SubwayError(Exception):
    """Base class for all domain-specific errors raised by this program."""


class DataLoadError(SubwayError):
    """Raised when the subway dataset cannot be read or is malformed."""


class InputFormatError(SubwayError):
    """Raised when a user query does not follow the 'Start; End' format."""


class StationNotFoundError(SubwayError):
    """Raised when a station name does not exist in the network."""


class InvalidQueryError(SubwayError):
    """Raised when a query is logically invalid (e.g. same start and end)."""


class PathNotFoundError(SubwayError):
    """Raised when no path can be found between two stations."""


class FareCalculationError(SubwayError):
    """Raised when a fare cannot be calculated from the given input."""
