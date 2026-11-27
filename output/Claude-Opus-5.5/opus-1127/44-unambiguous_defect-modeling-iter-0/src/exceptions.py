"""Exception hierarchy for the Beijing Subway fare calculation system.

Each class corresponds to one level of the error handling scheme:
input format errors, unknown stations, logical errors, path calculation
errors and fare calculation errors.
"""


class SubwayError(Exception):
    """Base class for all errors raised by the subway system."""


class InputFormatError(SubwayError):
    """Raised when the user input cannot be parsed into two station names."""


class StationNotFoundError(SubwayError):
    """Raised when a station name does not exist in the network."""


class InvalidQueryError(SubwayError):
    """Raised when a query is logically invalid (e.g. start == end)."""


class PathCalculationError(SubwayError):
    """Raised when a path cannot be calculated."""


class FareCalculationError(SubwayError):
    """Raised when the fare cannot be calculated."""


class DataError(SubwayError):
    """Raised when subway data cannot be loaded or updated."""
