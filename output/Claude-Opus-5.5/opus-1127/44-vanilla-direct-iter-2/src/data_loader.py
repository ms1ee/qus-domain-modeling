"""
Data loading utilities for the Beijing Subway fare calculation system.

The subway network data lives in ``subway_data.json`` next to this module.
``DATA_FILE_PATH`` is computed from this file's own location, so it is valid
no matter which working directory the program is started from.
"""

import json
import os

DATA_FILE_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "subway_data.json")


class DataFormatError(ValueError):
    """Raised when the subway data file does not have the expected structure."""


def load_subway_data(path=DATA_FILE_PATH):
    """Load the subway JSON data file and return its content as a dict.

    Expected structure::

        {"stations": [{"name": str, "lines": [str]}],
         "connections": [{"source": str, "dest": str,
                          "distance": int, "line": str}]}

    Raises:
        FileNotFoundError: if the file does not exist.
        json.JSONDecodeError: if the file is not valid JSON.
        DataFormatError: if the top-level structure is wrong.
    """
    if path is None:
        path = DATA_FILE_PATH
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    if not isinstance(data, dict):
        raise DataFormatError("Subway data must be a JSON object")
    data.setdefault("stations", [])
    data.setdefault("connections", [])
    if not isinstance(data["stations"], list) or not isinstance(data["connections"], list):
        raise DataFormatError("'stations' and 'connections' must be lists")
    return data


def save_subway_data(data, path=DATA_FILE_PATH):
    """Write subway data back to a JSON file (used by the data update mechanism)."""
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
