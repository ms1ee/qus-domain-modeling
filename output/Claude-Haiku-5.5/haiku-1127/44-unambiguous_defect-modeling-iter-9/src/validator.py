"""Input parsing and validation for station queries."""

import re

FORMAT_MESSAGE = "Input format incorrect, please use 'Starting Station; Ending Station' format"

# Accepted separators between the two station names.
_SEPARATOR_RE = re.compile(r"[;；,，]")


class QueryError(Exception):
    """Base class for user input problems."""


class InputFormatError(QueryError):
    """The query text does not contain exactly two station names."""


class StationNotFoundError(QueryError):
    """A station name does not match any official station."""


class SameStationError(QueryError):
    """Starting and ending stations are identical."""


class InputValidator:
    """Parses and validates "Starting Station; Ending Station" queries."""

    def __init__(self, network):
        self.network = network
        self.separator = ";"
        self.official_station_names = network.station_names()

    def parse(self, text):
        """Split the query text into raw (start, end) names.

        Raises:
            InputFormatError: if the text is not two non-empty names.
        """
        if text is None or not str(text).strip():
            raise InputFormatError(FORMAT_MESSAGE)
        parts = [part.strip() for part in _SEPARATOR_RE.split(str(text).strip())]
        if len(parts) != 2 or not parts[0] or not parts[1]:
            raise InputFormatError(FORMAT_MESSAGE)
        return parts[0], parts[1]

    def standardize_station(self, raw_name, role):
        """Return the official name for ``raw_name``.

        Args:
            raw_name: name typed by the user.
            role: "Starting" or "Ending", used in error messages.

        Raises:
            StationNotFoundError: if no official station matches.
        """
        canonical = self.network.standardize_name(raw_name)
        if canonical is None:
            raise StationNotFoundError(
                f"{role} station '{raw_name}' does not exist, please check the station name"
            )
        return canonical

    def validate(self, text):
        """Parse and validate a query.

        Returns:
            (official starting station, official ending station)

        Raises:
            QueryError subclasses describing the first problem found.
        """
        raw_start, raw_end = self.parse(text)
        start = self.standardize_station(raw_start, "Starting")
        end = self.standardize_station(raw_end, "Ending")
        if start == end:
            raise SameStationError("Starting station cannot be the same as the ending station")
        return start, end
