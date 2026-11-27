"""Custom exception hierarchy for the Beijing Subway fare calculation system."""


class SubwayError(Exception):
    """Base class for all domain errors raised by the program."""


class DataLoadError(SubwayError):
    """Raised when the subway data file is missing, unreadable or malformed."""


class InputFormatError(SubwayError):
    """Raised when a user query does not follow the 'Starting; Ending' format."""


class StationNotFoundError(SubwayError):
    """Raised when a referenced station does not exist in the network."""


class InvalidQueryError(SubwayError):
    """Raised for logically invalid requests, e.g. identical start and end stations."""


class PathNotFoundError(SubwayError):
    """Raised when no route satisfies the query (e.g. transfer limit too strict)."""


class FareCalculationError(SubwayError, ValueError):
    """Raised when a fare or time estimate cannot be computed from the given input."""


class ReportExportError(SubwayError):
    """Raised when a report cannot be written to the requested output file."""
