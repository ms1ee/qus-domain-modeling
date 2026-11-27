"""
Data loading utilities for the Beijing Subway fare calculation system.

The subway network data lives in ``subway_data.json`` next to this module.
``DATA_FILE_PATH`` is an absolute path, so it is valid from any working
directory.

File layout::

    {
      "stations":    [{"name": str, "lines": [str, ...]}, ...],
      "connections": [{"source": str, "dest": str,
                       "distance": int (meters), "line": str}, ...]
    }
"""

import json
import os

#: Absolute path of the bundled subway data file (src/subway_data.json).
DATA_FILE_PATH = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "subway_data.json"
)


class DataLoadError(Exception):
    """Raised when the subway data file cannot be read or parsed."""


def load_subway_data(path=DATA_FILE_PATH):
    """Load the subway data JSON file and return its content as a dict.

    :param path: path of the JSON data file (defaults to ``DATA_FILE_PATH``)
    :return: the parsed JSON content (a dict)
    :raises DataLoadError: if the file is missing, unreadable or malformed
    """
    if path is None:
        path = DATA_FILE_PATH
    try:
        with open(path, "r", encoding="utf-8") as fh:
            data = json.load(fh)
    except FileNotFoundError as exc:
        raise DataLoadError(f"Data file not found: {path}") from exc
    except json.JSONDecodeError as exc:
        raise DataLoadError(f"Data file is not valid JSON: {path} ({exc})") from exc
    except OSError as exc:
        raise DataLoadError(f"Cannot read data file: {path} ({exc})") from exc

    if not isinstance(data, dict):
        raise DataLoadError(f"Data file must contain a JSON object: {path}")
    data.setdefault("stations", [])
    data.setdefault("connections", [])
    return data
