"""Loading of the Beijing Subway dataset stored in ``subway_data.json``.

The dataset has the form::

    {"stations": [{"name": str, "lines": [str]}],
     "connections": [{"source": str, "dest": str, "distance": int, "line": str}]}

Distances are in meters.
"""

import json
import os

# Absolute path of the bundled dataset; valid regardless of the working directory.
DATA_FILE_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "subway_data.json")


class DataLoadError(Exception):
    """Raised when the subway dataset is missing, unreadable or malformed."""


def _validate_data(data):
    """Check the structure of the loaded dataset.

    Raises:
        DataLoadError: if the structure does not match the expected format.
    """
    if not isinstance(data, dict):
        raise DataLoadError("Subway data must be a JSON object")

    stations = data.get("stations")
    connections = data.get("connections")
    if not isinstance(stations, list):
        raise DataLoadError("'stations' must be a list")
    if not isinstance(connections, list):
        raise DataLoadError("'connections' must be a list")

    for index, station in enumerate(stations):
        if not isinstance(station, dict) or not isinstance(station.get("name"), str):
            raise DataLoadError(f"Station record #{index} must contain a string 'name'")
        lines = station.get("lines", [])
        if not isinstance(lines, list) or not all(isinstance(item, str) for item in lines):
            raise DataLoadError(f"Station record #{index} has an invalid 'lines' field")

    for index, conn in enumerate(connections):
        if not isinstance(conn, dict):
            raise DataLoadError(f"Connection record #{index} must be an object")
        for key in ("source", "dest", "line"):
            if not isinstance(conn.get(key), str):
                raise DataLoadError(f"Connection record #{index} must contain a string '{key}'")
        distance = conn.get("distance")
        if isinstance(distance, bool) or not isinstance(distance, (int, float)):
            raise DataLoadError(f"Connection record #{index} must contain a numeric 'distance'")


def load_subway_data(path=DATA_FILE_PATH):
    """Load and validate the subway dataset.

    Args:
        path: path of the JSON file (defaults to ``src/subway_data.json``).

    Returns:
        dict: the JSON content of the file.

    Raises:
        DataLoadError: if the file cannot be read, is not valid JSON, or has
            an unexpected structure.
    """
    try:
        with open(path, "r", encoding="utf-8") as handle:
            data = json.load(handle)
    except FileNotFoundError as exc:
        raise DataLoadError(f"Subway data file not found: {path}") from exc
    except json.JSONDecodeError as exc:
        raise DataLoadError(f"Subway data file is not valid JSON: {exc}") from exc
    except OSError as exc:
        raise DataLoadError(f"Cannot read subway data file {path}: {exc}") from exc

    _validate_data(data)
    return data
