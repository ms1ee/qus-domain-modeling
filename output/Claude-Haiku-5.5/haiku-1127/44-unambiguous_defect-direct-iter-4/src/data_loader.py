"""Loading and saving of the Beijing Subway dataset (src/subway_data.json).

The dataset JSON has the form:
    {"stations": [{"name": str, "lines": [str]}],
     "connections": [{"source": str, "dest": str, "distance": int, "line": str}]}
"""

import json
import os

_THIS_DIR = os.path.dirname(os.path.abspath(__file__))

# Absolute path of src/subway_data.json, valid regardless of the working directory.
DATA_FILE_PATH = os.path.join(_THIS_DIR, "subway_data.json")


class DataLoadError(Exception):
    """Raised when the subway dataset cannot be read, parsed or saved."""


def load_subway_data(path=DATA_FILE_PATH) -> dict:
    """Read the subway dataset file and return its JSON content as a dict.

    Args:
        path: Path to the JSON dataset file.

    Returns:
        The parsed dataset dictionary with 'stations' and 'connections' lists.

    Raises:
        DataLoadError: If the file is missing, unreadable, not valid JSON,
            or does not have the expected structure.
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
        raise DataLoadError("Subway data must be a JSON object")
    stations = data.get("stations", [])
    connections = data.get("connections", [])
    if not isinstance(stations, list) or not isinstance(connections, list):
        raise DataLoadError("'stations' and 'connections' must both be lists")
    data["stations"] = stations
    data["connections"] = connections
    return data


def save_subway_data(data: dict, path=DATA_FILE_PATH) -> None:
    """Write a dataset dictionary back to a JSON file.

    Args:
        data: Dataset dictionary in the same format returned by load_subway_data.
        path: Destination file path.

    Raises:
        DataLoadError: If the file cannot be written.
    """
    try:
        with open(path, "w", encoding="utf-8") as handle:
            json.dump(data, handle, ensure_ascii=False, indent=2)
            handle.write("\n")
    except OSError as exc:
        raise DataLoadError(f"Cannot write subway data file: {path} ({exc})") from exc
