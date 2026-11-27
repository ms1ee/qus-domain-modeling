"""Input parsing and validation for the command-line interface.

Handles station-name standardization, "Starting Station; Ending Station" format
parsing, existence checks and logical checks.
"""

import re
import unicodedata

FORMAT_HINT = "Input format incorrect, please use 'Starting Station; Ending Station' format"

_SEPARATOR_PATTERN = re.compile(r"[;；,，]")


class ValidationError(ValueError):
    """Raised when user input fails format, existence or logic validation."""


def normalize_key(name) -> str:
    """Return a comparison key for a name: NFKC-normalized, lower-case, no spaces,
    and without a trailing 站 (station) suffix."""
    text = unicodedata.normalize("NFKC", str(name)).strip()
    text = re.sub(r"\s+", "", text).lower()
    if len(text) > 1 and text.endswith("站"):
        text = text[:-1]
    return text


def parse_station_pair(text) -> tuple:
    """Split 'Starting Station; Ending Station' input into two raw names.

    Accepts ';', '；', ',' or '，' as separators.

    Raises:
        ValidationError: If the input does not contain exactly two non-empty parts.
    """
    if text is None:
        raise ValidationError(FORMAT_HINT)
    parts = [part.strip() for part in _SEPARATOR_PATTERN.split(str(text))]
    if len(parts) != 2 or not parts[0] or not parts[1]:
        raise ValidationError(FORMAT_HINT)
    return parts[0], parts[1]


def resolve_station(raw_name, official_names, role="Starting") -> str:
    """Map a user-entered station name to its official name.

    Args:
        raw_name: The name typed by the user.
        official_names: Iterable of official station names.
        role: "Starting" or "Ending", used in error messages.

    Raises:
        ValidationError: If no official station matches.
    """
    key = normalize_key(raw_name)
    for name in official_names:
        if normalize_key(name) == key:
            return name
    raise ValidationError(
        f"{role} station '{raw_name}' does not exist, please check the station name"
    )


def validate_query(text, official_names) -> tuple:
    """Parse and validate a full query. Returns (start_name, end_name) official names.

    Raises:
        ValidationError: On format, existence or logical errors.
    """
    raw_start, raw_end = parse_station_pair(text)
    names = list(official_names)
    start = resolve_station(raw_start, names, "Starting")
    end = resolve_station(raw_end, names, "Ending")
    if start == end:
        raise ValidationError("Starting station cannot be the same as the ending station")
    return start, end


def resolve_line(raw_name, known_lines):
    """Return the official line name matching ``raw_name``, or None if unknown."""
    key = normalize_key(raw_name)
    for line in known_lines:
        if normalize_key(line) == key:
            return line
    return None
