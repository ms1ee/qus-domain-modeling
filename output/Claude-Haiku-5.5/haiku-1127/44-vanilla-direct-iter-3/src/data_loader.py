"""Loading, validation and saving of the Beijing Subway dataset (subway_data.json)."""

import json
import os
from numbers import Number


DATA_FILE_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "subway_data.json")


class DataFormatError(ValueError):
    """Raised when the subway dataset does not follow the expected structure."""


def _is_number(value) -> bool:
    """Return True for int/float values, excluding booleans."""
    return isinstance(value, Number) and not isinstance(value, bool)


def validate_subway_data(data) -> None:
    """Check the structure of a subway dataset.

    Expected structure:
        {"stations": [{"name": str, "lines": [str]}],
         "connections": [{"source": str, "dest": str, "distance": int, "line": str}]}

    Raises:
        DataFormatError: if the structure is invalid.
    """
    if not isinstance(data, dict):
        raise DataFormatError("Subway data must be a JSON object")

    stations = data.get("stations")
    connections = data.get("connections")
    if not isinstance(stations, list):
        raise DataFormatError("'stations' must be a list")
    if not isinstance(connections, list):
        raise DataFormatError("'connections' must be a list")

    for index, station in enumerate(stations):
        if not isinstance(station, dict):
            raise DataFormatError(f"Station #{index} must be an object")
        name = station.get("name")
        if not isinstance(name, str) or not name.strip():
            raise DataFormatError(f"Station #{index} has an invalid 'name'")
        lines = station.get("lines", [])
        if not isinstance(lines, list) or not all(isinstance(line, str) for line in lines):
            raise DataFormatError(f"Station '{name}' has invalid 'lines'")

    for index, conn in enumerate(connections):
        if not isinstance(conn, dict):
            raise DataFormatError(f"Connection #{index} must be an object")
        for key in ("source", "dest", "line"):
            if not isinstance(conn.get(key), str) or not conn.get(key).strip():
                raise DataFormatError(f"Connection #{index} has an invalid '{key}'")
        distance = conn.get("distance")
        if not _is_number(distance) or distance <= 0:
            raise DataFormatError(f"Connection #{index} has an invalid 'distance'")


def load_subway_data(path=DATA_FILE_PATH) -> dict:
    """Load and validate the subway dataset from a JSON file.

    Returns:
        The JSON content of the file as a dict.
    """
    with open(path, "r", encoding="utf-8") as handle:
        data = json.load(handle)
    validate_subway_data(data)
    return data


def save_subway_data(data: dict, path=DATA_FILE_PATH) -> None:
    """Validate and write a subway dataset to a JSON file."""
    validate_subway_data(data)
    with open(path, "w", encoding="utf-8") as handle:
        json.dump(data, handle, ensure_ascii=False, indent=2)
        handle.write("\n")
