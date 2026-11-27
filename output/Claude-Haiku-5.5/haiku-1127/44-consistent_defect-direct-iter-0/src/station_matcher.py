"""Station name standardisation and nearest-match lookup."""

import difflib
import re
from typing import NamedTuple


class StationNotFoundError(Exception):
    """Raised when no station resembles the given name."""

    def __init__(self, raw_name):
        self.raw_name = raw_name
        super().__init__(f"Station '{raw_name}' does not exist, please check the station name")


class InputFormatError(Exception):
    """Raised when user input does not follow the expected format."""


class MatchResult(NamedTuple):
    """Result of matching a user-supplied name.

    Attributes:
        name: The official station name.
        exact: True if the input matched the official name (ignoring surrounding spaces).
    """

    name: str
    exact: bool


def normalize_station_name(name):
    """Normalise a station name for comparison.

    Removes whitespace, lowercases, and strips a trailing "station"/"站" suffix.
    """
    text = re.sub(r"\s+", "", str(name)).lower()
    for suffix in ("station", "站"):
        if text.endswith(suffix) and len(text) > len(suffix):
            text = text[: -len(suffix)]
            break
    return text


class StationMatcher:
    """Matches user-supplied station names to official names.

    Lookup order: normalised exact match, then nearest fuzzy match
    (difflib, cutoff 0.6). Unknown names with no close match raise
    StationNotFoundError.
    """

    def __init__(self, station_names):
        self._index = {}
        for name in station_names:
            self._index.setdefault(normalize_station_name(name), name)

    def standardize(self, raw_name):
        """Return the official station matching raw_name.

        Raises:
            InputFormatError: If raw_name is empty.
            StationNotFoundError: If no station is close enough.
        """
        if raw_name is None or not str(raw_name).strip():
            raise InputFormatError("Station name must not be empty")
        stripped = str(raw_name).strip()
        key = normalize_station_name(stripped)
        if key in self._index:
            name = self._index[key]
            return MatchResult(name, name == stripped)
        close = difflib.get_close_matches(key, list(self._index.keys()), n=1, cutoff=0.6)
        if not close:
            raise StationNotFoundError(stripped)
        return MatchResult(self._index[close[0]], False)
