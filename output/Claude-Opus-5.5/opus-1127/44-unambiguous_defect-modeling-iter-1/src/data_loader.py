"""
Data loading utilities for the Beijing Subway fare calculation system.

The subway network data lives in ``subway_data.json`` next to this module.
``DATA_FILE_PATH`` is an absolute path, so it is valid regardless of the
current working directory.
"""

import json
import os

#: Absolute path of the bundled subway data file (src/subway_data.json).
DATA_FILE_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "subway_data.json")


class DataLoadError(Exception):
    """Raised when the subway data file cannot be read or is malformed."""


def load_subway_data(path=DATA_FILE_PATH):
    """
    Load the subway network JSON file and return its content as a dict.

    Expected structure::

        {"stations": [{"name": str, "lines": [str]}],
         "connections": [{"source": str, "dest": str,
                          "distance": int, "line": str}]}

    :param path: path of the JSON file (defaults to ``DATA_FILE_PATH``)
    :return: the parsed JSON content (dict)
    :raises FileNotFoundError: if the file does not exist
    :raises DataLoadError: if the file content is not valid subway data
    """
    if path is None:
        path = DATA_FILE_PATH
    with open(path, "r", encoding="utf-8") as fh:
        try:
            data = json.load(fh)
        except json.JSONDecodeError as exc:
            raise DataLoadError(f"Invalid JSON in data file '{path}': {exc}") from exc

    if not isinstance(data, dict):
        raise DataLoadError(f"Data file '{path}' must contain a JSON object")
    data.setdefault("stations", [])
    data.setdefault("connections", [])
    if not isinstance(data["stations"], list) or not isinstance(data["connections"], list):
        raise DataLoadError(f"Data file '{path}' has invalid 'stations'/'connections' fields")
    return data


def save_subway_data(data, path=DATA_FILE_PATH):
    """Write subway data back to a JSON file (used by the data update mechanism)."""
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(data, fh, ensure_ascii=False, indent=2)
