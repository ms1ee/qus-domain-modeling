"""Custom exception hierarchy for the Beijing Subway fare calculation system."""


class SubwayError(Exception):
    """Base class for all errors raised by the subway fare system."""


class DataError(SubwayError, ValueError):
    """Raised when subway data is missing, malformed or inconsistent."""


class InvalidInputError(SubwayError, ValueError):
    """Raised when user input has an invalid format or a logical problem."""


class StationNotFoundError(SubwayError, LookupError):
    """Raised when a station name does not exist in the network."""


class PathCalculationError(SubwayError, RuntimeError):
    """Raised when path computation fails unexpectedly."""


class PathNotFoundError(PathCalculationError):
    """Raised when no path exists between two stations under the given constraints."""


class FareCalculationError(SubwayError, ValueError):
    """Raised when fare or travel-time estimation receives invalid values."""
