"""Data loading utilities for the Beijing Subway fare calculation system.

The subway network data lives in ``subway_data.json`` next to this module.
:data:`DATA_FILE_PATH` is an absolute path, so it is valid regardless of the
current working directory.
"""

import json
import os

DATA_FILE_PATH = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "subway_data.json"
)


class DataFormatError(ValueError):
    """Raised when the subway data file does not have the expected structure."""


def load_subway_data(path=DATA_FILE_PATH):
    """Load and return the JSON content of the subway data file.

    Args:
        path: Path of the JSON data file. Defaults to :data:`DATA_FILE_PATH`.

    Returns:
        dict: The parsed JSON content, with ``stations`` and ``connections`` keys.

    Raises:
        FileNotFoundError: If the file does not exist.
        ValueError: If the file is not valid JSON or has an unexpected structure.
    """
    if path is None:
        path = DATA_FILE_PATH
    with open(path, "r", encoding="utf-8") as handle:
        data = json.load(handle)
    if not isinstance(data, dict):
        raise DataFormatError("Subway data must be a JSON object")
    data.setdefault("stations", [])
    data.setdefault("connections", [])
    if not isinstance(data["stations"], list):
        raise DataFormatError("'stations' must be a list")
    if not isinstance(data["connections"], list):
        raise DataFormatError("'connections' must be a list")
    return data


def save_subway_data(data, path=DATA_FILE_PATH):
    """Write subway data back to a JSON file (UTF-8, human readable)."""
    with open(path, "w", encoding="utf-8") as handle:
        json.dump(data, handle, ensure_ascii=False, indent=2)
