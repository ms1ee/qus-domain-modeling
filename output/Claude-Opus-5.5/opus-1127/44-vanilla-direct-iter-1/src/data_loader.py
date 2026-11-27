"""Data loading utilities for the Beijing Subway fare calculation system.

The network data lives in ``subway_data.json`` next to this module.  Its
layout is::

    {"stations": [{"name": str, "lines": [str]}],
     "connections": [{"source": str, "dest": str,
                      "distance": int, "line": str}]}
"""

import json
import os

# Absolute path of the bundled data file, valid from any working directory.
DATA_FILE_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                              "subway_data.json")


class DataLoadError(Exception):
    """Raised when the subway data file cannot be read or is malformed."""


def load_subway_data(path=DATA_FILE_PATH):
    """Load and return the JSON content of the subway data file.

    :param path: path of the JSON data file (defaults to DATA_FILE_PATH)
    :return: dict with "stations" and "connections" keys
    :raises DataLoadError: if the file is missing or not valid JSON
    """
    if path is None:
        path = DATA_FILE_PATH
    try:
        with open(path, "r", encoding="utf-8") as fh:
            data = json.load(fh)
    except FileNotFoundError as exc:
        raise DataLoadError("Data file not found: %s" % path) from exc
    except json.JSONDecodeError as exc:
        raise DataLoadError("Data file is not valid JSON: %s (%s)" % (path, exc)) from exc
    except OSError as exc:
        raise DataLoadError("Cannot read data file %s: %s" % (path, exc)) from exc
    if not isinstance(data, dict):
        raise DataLoadError("Data file root must be a JSON object")
    data.setdefault("stations", [])
    data.setdefault("connections", [])
    return data


def save_subway_data(data, path=DATA_FILE_PATH):
    """Write subway data back to a JSON file."""
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(data, fh, ensure_ascii=False, indent=2)
