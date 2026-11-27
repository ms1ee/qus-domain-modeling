"""Loading and saving of the Beijing Subway network dataset (subway_data.json).

The dataset has the following structure:
    {"stations": [{"name": str, "lines": [str]}],
     "connections": [{"source": str, "dest": str, "distance": int, "line": str}]}
Distances are in meters.
"""

import json
import os

from models import SubwayError

# Absolute path of subway_data.json, valid regardless of the current working directory.
DATA_FILE_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "subway_data.json")


class DataLoadError(SubwayError):
    """Raised when the subway dataset cannot be read, written or is malformed."""


def load_subway_data(path=DATA_FILE_PATH):
    """Load the subway dataset from ``path`` and return its JSON content as a dict.

    Raises DataLoadError if the file is missing, unreadable, not valid JSON,
    or does not contain the required 'stations' and 'connections' lists.
    """
    try:
        with open(path, "r", encoding="utf-8") as handle:
            data = json.load(handle)
    except FileNotFoundError as exc:
        raise DataLoadError(f"Subway data file not found: {path}") from exc
    except json.JSONDecodeError as exc:
        raise DataLoadError(f"Subway data file is not valid JSON: {path} ({exc})") from exc
    except OSError as exc:
        raise DataLoadError(f"Cannot read subway data file: {path} ({exc})") from exc

    if not isinstance(data, dict):
        raise DataLoadError(f"Subway data root must be a JSON object: {path}")
    for key in ("stations", "connections"):
        if not isinstance(data.get(key), list):
            raise DataLoadError(f"Missing or invalid '{key}' list in {path}")
    return data


def save_subway_data(data, path=DATA_FILE_PATH):
    """Write the dataset dictionary back to ``path`` as formatted UTF-8 JSON."""
    try:
        with open(path, "w", encoding="utf-8") as handle:
            json.dump(data, handle, ensure_ascii=False, indent=2)
            handle.write("\n")
    except OSError as exc:
        raise DataLoadError(f"Cannot write subway data file: {path} ({exc})") from exc
