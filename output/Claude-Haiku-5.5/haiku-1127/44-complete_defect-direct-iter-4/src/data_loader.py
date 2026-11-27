"""Loading of the Beijing Subway dataset from ``subway_data.json``.

The dataset has the following structure::

    {"stations": [{"name": str, "lines": [str]}],
     "connections": [{"source": str, "dest": str, "distance": int, "line": str}]}

``distance`` is expressed in meters.
"""

import json
import os
from typing import Any, Dict

# Absolute path of the data file, valid regardless of the current working directory.
DATA_FILE_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "subway_data.json")


class DataLoadError(Exception):
    """Raised when the subway dataset cannot be read or is malformed."""


def _validate(data: Any, path: str) -> None:
    """Validate the basic structure of the loaded subway dataset.

    Raises:
        DataLoadError: if the structure does not match the expected schema.
    """
    if not isinstance(data, dict):
        raise DataLoadError(f"{path}: top-level JSON value must be an object")

    stations = data.get("stations")
    connections = data.get("connections")
    if not isinstance(stations, list):
        raise DataLoadError(f"{path}: 'stations' must be a list")
    if not isinstance(connections, list):
        raise DataLoadError(f"{path}: 'connections' must be a list")

    for index, station in enumerate(stations):
        if not isinstance(station, dict):
            raise DataLoadError(f"{path}: station #{index} must be an object")
        name = station.get("name")
        if not isinstance(name, str) or not name.strip():
            raise DataLoadError(f"{path}: station #{index} has no valid 'name'")
        lines = station.get("lines", [])
        if not isinstance(lines, list) or not all(isinstance(line, str) for line in lines):
            raise DataLoadError(f"{path}: station '{name}' has an invalid 'lines' field")

    for index, conn in enumerate(connections):
        if not isinstance(conn, dict):
            raise DataLoadError(f"{path}: connection #{index} must be an object")
        for key in ("source", "dest", "line"):
            if not isinstance(conn.get(key), str):
                raise DataLoadError(f"{path}: connection #{index} has no valid '{key}'")
        distance = conn.get("distance")
        if isinstance(distance, bool) or not isinstance(distance, (int, float)):
            raise DataLoadError(f"{path}: connection #{index} has no valid 'distance'")


def load_subway_data(path: str = DATA_FILE_PATH) -> Dict[str, Any]:
    """Read and validate the subway dataset.

    Args:
        path: path of the JSON file. Defaults to ``DATA_FILE_PATH``.

    Returns:
        The JSON content of the file as a dictionary.

    Raises:
        DataLoadError: if the file is missing, unreadable, not valid JSON,
            or does not match the expected schema.
    """
    try:
        with open(path, "r", encoding="utf-8") as handle:
            data = json.load(handle)
    except FileNotFoundError as exc:
        raise DataLoadError(f"Data file not found: {path}") from exc
    except OSError as exc:
        raise DataLoadError(f"Cannot read data file {path}: {exc}") from exc
    except json.JSONDecodeError as exc:
        raise DataLoadError(f"Data file {path} is not valid JSON: {exc}") from exc

    _validate(data, path)
    return data
