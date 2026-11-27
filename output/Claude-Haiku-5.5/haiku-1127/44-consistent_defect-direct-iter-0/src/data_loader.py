"""Loading and saving of the Beijing Subway dataset (subway_data.json).

The dataset has the following shape:
    {"stations": [{"name": str, "lines": [str]}],
     "connections": [{"source": str, "dest": str, "distance": int, "line": str}]}
"""

import json
import os

# Absolute path of src/subway_data.json, valid from any working directory.
DATA_FILE_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "subway_data.json")


class DataLoadError(Exception):
    """Raised when the subway dataset cannot be read or is malformed."""


def _validate(data, path):
    """Validate the structure of the loaded dataset and normalise field types.

    Args:
        data: The parsed JSON value.
        path: File path used in error messages.

    Returns:
        The validated (and normalised) dataset dictionary.

    Raises:
        DataLoadError: If the structure is invalid.
    """
    if not isinstance(data, dict):
        raise DataLoadError(f"{path}: top-level JSON value must be an object")

    for key in ("stations", "connections"):
        if key not in data:
            data[key] = []
        if not isinstance(data[key], list):
            raise DataLoadError(f"{path}: '{key}' must be a list")

    for index, station in enumerate(data["stations"]):
        if not isinstance(station, dict):
            raise DataLoadError(f"{path}: station entry {index} must be an object")
        name = station.get("name")
        if not isinstance(name, str) or not name.strip():
            raise DataLoadError(f"{path}: station entry {index} has an invalid 'name'")
        lines = station.get("lines", [])
        if not isinstance(lines, list):
            raise DataLoadError(f"{path}: station '{name}' has invalid 'lines'")
        station["name"] = name.strip()
        station["lines"] = [str(line) for line in lines]

    for index, conn in enumerate(data["connections"]):
        if not isinstance(conn, dict):
            raise DataLoadError(f"{path}: connection entry {index} must be an object")
        for key in ("source", "dest", "line"):
            if not isinstance(conn.get(key), str):
                raise DataLoadError(f"{path}: connection entry {index} has invalid '{key}'")
        distance = conn.get("distance")
        if isinstance(distance, bool) or not isinstance(distance, (int, float)) or distance < 0:
            raise DataLoadError(f"{path}: connection entry {index} has invalid 'distance'")
        conn["distance"] = int(distance)

    return data


def load_subway_data(path=DATA_FILE_PATH):
    """Load the subway dataset from a JSON file.

    Args:
        path: Path to the JSON file. Defaults to DATA_FILE_PATH.

    Returns:
        dict: The JSON content of the file.

    Raises:
        DataLoadError: If the file is missing, unreadable, or malformed.
    """
    try:
        with open(path, "r", encoding="utf-8") as handle:
            data = json.load(handle)
    except FileNotFoundError as exc:
        raise DataLoadError(f"Subway data file not found: {path}") from exc
    except json.JSONDecodeError as exc:
        raise DataLoadError(f"Invalid JSON in {path}: {exc}") from exc
    except OSError as exc:
        raise DataLoadError(f"Cannot read subway data file {path}: {exc}") from exc
    return _validate(data, path)


def save_subway_data(data, path=DATA_FILE_PATH):
    """Write the subway dataset back to a JSON file.

    Args:
        data: The dataset dictionary.
        path: Destination file path.

    Raises:
        DataLoadError: If the file cannot be written.
    """
    try:
        with open(path, "w", encoding="utf-8") as handle:
            json.dump(data, handle, ensure_ascii=False, indent=2)
            handle.write("\n")
    except OSError as exc:
        raise DataLoadError(f"Cannot write subway data file {path}: {exc}") from exc
