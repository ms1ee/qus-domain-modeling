"""Custom exception types shared by the Beijing Subway fare calculation system."""


class SubwayError(Exception):
    """Base class for all errors raised by the subway fare system."""


class InputFormatError(SubwayError):
    """Raised when a user query does not follow the 'Start; End' format."""


class StationNotFoundError(SubwayError):
    """Raised when a station name cannot be matched to the official network."""

    def __init__(self, station_name, message=None):
        self.station_name = station_name
        super().__init__(
            message or f"Station '{station_name}' does not exist, please check the station name"
        )


class QueryLogicError(SubwayError):
    """Raised when a query is logically invalid (e.g. identical start and end)."""


class PathNotFoundError(SubwayError):
    """Raised when no route satisfies the requested constraints."""


class PathCalculationError(SubwayError):
    """Raised when an unexpected failure occurs during path calculation."""


class FareCalculationError(SubwayError):
    """Raised when the fare for a route cannot be calculated."""


class DataError(SubwayError):
    """Raised when subway data is missing, malformed, or inconsistent."""
