"""Parsing and validation of user queries in the 'Starting Station; Ending Station' format."""

import re

_QUERY_SPLIT = re.compile(r"[;；,，]")


class QueryError(Exception):
    """Base class for user-input problems."""


class InputFormatError(QueryError):
    """The query does not contain exactly two station names."""

    def __init__(self):
        super().__init__(
            "Input format incorrect, please use 'Starting Station; Ending Station' format"
        )


class UnknownStationError(QueryError):
    """A station name does not exist in the network."""

    def __init__(self, role, name):
        super().__init__(
            f"{role} station '{name}' does not exist, please check the station name"
        )
        self.role = role
        self.name = name


class SameStationError(QueryError):
    """Starting and ending stations are identical."""

    def __init__(self):
        super().__init__("Starting station cannot be the same as the ending station")


def parse_query(text):
    """Split a query into raw starting and ending station names.

    Accepted separators: ``;``, ``,`` and their full-width forms.

    Returns:
        tuple: ``(start_raw, end_raw)``.

    Raises:
        InputFormatError: If the text does not contain exactly two non-empty parts.
    """
    if not isinstance(text, str):
        raise InputFormatError()
    parts = [part.strip() for part in _QUERY_SPLIT.split(text.strip())]
    if len(parts) != 2 or not all(parts):
        raise InputFormatError()
    return parts[0], parts[1]


def resolve_query(text, network):
    """Parse a query and standardise both station names against the network.

    Returns:
        tuple: Official ``(start, end)`` station names.

    Raises:
        InputFormatError, UnknownStationError, SameStationError
    """
    raw_start, raw_end = parse_query(text)
    start = network.resolve_station_name(raw_start)
    if start is None:
        raise UnknownStationError("Starting", raw_start)
    end = network.resolve_station_name(raw_end)
    if end is None:
        raise UnknownStationError("Ending", raw_end)
    if start == end:
        raise SameStationError()
    return start, end


def parse_line_preference(text):
    """Parse a comma-separated list of preferred line names, e.g. ``"Line 1, Line 2"``."""
    if not text:
        return []
    return [part.strip() for part in text.split(",") if part.strip()]
