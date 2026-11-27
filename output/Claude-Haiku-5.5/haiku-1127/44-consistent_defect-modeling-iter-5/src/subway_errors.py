"""Custom exception hierarchy for the Beijing Subway fare calculation system."""


class SubwayError(Exception):
    """Base class for all errors raised by the subway fare system."""


class InputFormatError(SubwayError):
    """Raised when a user query does not follow the 'Starting Station; Ending Station' format."""


class StationNotFoundError(SubwayError):
    """Raised when a station name cannot be resolved to any known station."""


class SameStationError(SubwayError):
    """Raised when the starting station and the ending station are identical."""


class RouteNotFoundError(SubwayError):
    """Raised when no path exists between the two stations under the current constraints."""


class FareCalculationError(SubwayError):
    """Raised when a fare cannot be calculated for the given distance."""


class DataError(SubwayError):
    """Raised when the subway dataset is missing, unreadable or malformed."""


class DataUpdateError(SubwayError):
    """Raised when a data update request (add line, modify station, update distance) is invalid."""
