"""Custom exception hierarchy for the Beijing Subway fare calculation system."""


class SubwayError(Exception):
    """Base class for all domain errors raised by the system."""


class DataLoadError(SubwayError):
    """Raised when the subway dataset cannot be read or is structurally invalid."""


class DataUpdateError(SubwayError):
    """Raised when a data maintenance operation (add/modify/update) is rejected."""


class InvalidQueryError(SubwayError):
    """Raised when user input does not form a valid route query."""


class StationNotFoundError(SubwayError):
    """Raised when a station name cannot be matched to an official station."""


class PathNotFoundError(SubwayError):
    """Raised when no route exists between the requested stations."""
