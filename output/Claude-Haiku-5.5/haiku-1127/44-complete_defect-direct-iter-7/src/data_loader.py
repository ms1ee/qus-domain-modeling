"""Loading and saving of the Beijing Subway network data file.

The data file has the following structure:
    {"stations":    [{"name": str, "lines": [str]}],
     "connections": [{"source": str, "dest": str, "distance": int, "line": str}]}
Distances are in meters.
"""

import json
import os


class DataLoadError(Exception):
    """Raised when the subway data file cannot be read or is malformed."""


# Absolute path of src/subway_data.json, valid regardless of the working directory.
DATA_FILE_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "subway_data.json")


def _is_number(value):
    """Return True for int/float values that are not booleans."""
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def validate_subway_data(data):
    """Check the structure of the loaded subway data.

    Raises DataLoadError if the structure does not match the expected schema.
    """
    if not isinstance(data, dict):
        raise DataLoadError("Subway data must be a JSON object")

    stations = data.get("stations")
    connections = data.get("connections")
    if not isinstance(stations, list):
        raise DataLoadError("Subway data must contain a 'stations' list")
    if not isinstance(connections, list):
        raise DataLoadError("Subway data must contain a 'connections' list")

    for index, station in enumerate(stations):
        if not isinstance(station, dict) or not isinstance(station.get("name"), str):
            raise DataLoadError(f"Malformed station entry at index {index}")
        lines = station.get("lines", [])
        if not isinstance(lines, list) or not all(isinstance(line, str) for line in lines):
            raise DataLoadError(f"Station '{station.get('name')}' has malformed 'lines'")

    for index, conn in enumerate(connections):
        if not isinstance(conn, dict):
            raise DataLoadError(f"Malformed connection entry at index {index}")
        if not isinstance(conn.get("source"), str) or not isinstance(conn.get("dest"), str):
            raise DataLoadError(f"Connection at index {index} needs string 'source' and 'dest'")
        if not isinstance(conn.get("line"), str):
            raise DataLoadError(f"Connection at index {index} needs a string 'line'")
        if not _is_number(conn.get("distance")):
            raise DataLoadError(f"Connection at index {index} needs a numeric 'distance'")


def load_subway_data(path):
    """Load the subway data JSON file and return its content as a dict."""
    try:
        with open(path, "r", encoding="utf-8") as handle:
            data = json.load(handle)
    except FileNotFoundError as exc:
        raise DataLoadError(f"Subway data file not found: {path}") from exc
    except json.JSONDecodeError as exc:
        raise DataLoadError(f"Subway data file is not valid JSON: {exc}") from exc
    except OSError as exc:
        raise DataLoadError(f"Cannot read subway data file: {exc}") from exc

    validate_subway_data(data)
    return data


def save_subway_data(data, path):
    """Write the subway data to a JSON file atomically."""
    temp_path = path + ".tmp"
    try:
        with open(temp_path, "w", encoding="utf-8") as handle:
            json.dump(data, handle, ensure_ascii=False, indent=2)
        os.replace(temp_path, path)
    except OSError as exc:
        raise DataLoadError(f"Cannot write subway data file: {exc}") from exc
