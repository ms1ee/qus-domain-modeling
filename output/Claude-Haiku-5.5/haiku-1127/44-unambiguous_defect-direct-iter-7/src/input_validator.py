"""Validation and standardisation of user input.

Covers the "Starting Station; Ending Station" query format, station name
standardisation, station existence checks and line preference parsing.
"""

from __future__ import annotations

import difflib
import re
import unicodedata

from models import SubwayNetwork

QUERY_SEPARATOR_PATTERN = r"[;；,，]"
LIST_SEPARATOR_PATTERN = r"[,，;；]"


class ValidationError(ValueError):
    """Base class for invalid user input."""


class InputFormatError(ValidationError):
    """The query does not follow the 'Starting Station; Ending Station' format."""


class StationNotFoundError(ValidationError):
    """A station name does not match any station in the network."""

    def __init__(self, message: str, suggestions=None) -> None:
        super().__init__(message)
        self.suggestions = list(suggestions or [])


def normalize_text(text: str) -> str:
    """Apply Unicode normalisation and collapse whitespace."""
    text = unicodedata.normalize("NFKC", str(text)).strip()
    return re.sub(r"\s+", " ", text)


def parse_query(text: str) -> tuple[str, str]:
    """Split a query such as ``"Xizhimen; Guomen"`` into two station names.

    Raises:
        InputFormatError: If the text does not contain exactly two non-empty
            parts separated by ';' (full-width or ASCII) or ','.
    """
    message = "Input format incorrect, please use 'Starting Station; Ending Station' format"
    if text is None or not str(text).strip():
        raise InputFormatError(message)
    parts = re.split(QUERY_SEPARATOR_PATTERN, str(text))
    if len(parts) != 2:
        raise InputFormatError(message)
    start, end = normalize_text(parts[0]), normalize_text(parts[1])
    if not start or not end:
        raise InputFormatError(message)
    return start, end


def resolve_station(name: str, network: SubwayNetwork, role: str = "Starting") -> str:
    """Map a user-entered name to the official station name.

    Matching order: exact name, case-insensitive name, name with/without the
    trailing character '站' and name ignoring spaces.

    Args:
        name: Name entered by the user.
        network: The subway network.
        role: 'Starting' or 'Ending', used in error messages.

    Raises:
        StationNotFoundError: If no station matches.
    """
    cleaned = normalize_text(name)
    names = network.station_names()
    if cleaned in network.station_to_number:
        return cleaned

    casefold_map = {n.casefold(): n for n in names}
    if cleaned.casefold() in casefold_map:
        return casefold_map[cleaned.casefold()]

    candidates = [cleaned]
    if cleaned.endswith("站"):
        candidates.append(cleaned[:-1].rstrip())
    else:
        candidates.append(cleaned + "站")
    compact = cleaned.replace(" ", "")
    candidates.append(compact)
    for candidate in candidates:
        if candidate and candidate in network.station_to_number:
            return candidate
        if candidate and candidate.casefold() in casefold_map:
            return casefold_map[candidate.casefold()]

    suggestions = difflib.get_close_matches(cleaned, names, n=3, cutoff=0.6)
    message = f"{role} station '{cleaned}' does not exist, please check the station name"
    if suggestions:
        message += f". Did you mean: {', '.join(suggestions)}?"
    raise StationNotFoundError(message, suggestions)


def parse_line_preferences(text, network: SubwayNetwork) -> list[str]:
    """Parse a comma-separated list of line names such as ``"Line 1, Line 2"``.

    Returns:
        The official line names, in the order given, without duplicates.

    Raises:
        ValidationError: If a line name does not exist in the network.
    """
    if text is None:
        return []
    lookup = {line.casefold(): line for line in network.lines()}
    result: list[str] = []
    for part in re.split(LIST_SEPARATOR_PATTERN, str(text)):
        cleaned = normalize_text(part)
        if not cleaned:
            continue
        official = lookup.get(cleaned.casefold())
        if official is None:
            available = ", ".join(network.lines())
            raise ValidationError(
                f"Line '{cleaned}' does not exist, available lines: {available}"
            )
        if official not in result:
            result.append(official)
    return result
