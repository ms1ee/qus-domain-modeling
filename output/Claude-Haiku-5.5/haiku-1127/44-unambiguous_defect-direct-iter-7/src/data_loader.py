"""Loading and saving of the Beijing Subway data file.

The data file (``subway_data.json``) lives next to this module, so it can be
located from any working directory through ``DATA_FILE_PATH``.
"""

import json
import os

DATA_FILE_PATH = os.path.normpath(
    os.path.join(os.path.dirname(os.path.abspath(__file__)), "subway_data.json")
)


def load_subway_data(path=DATA_FILE_PATH) -> dict:
    """Load and validate the subway dataset.

    Args:
        path: Path of the JSON file to read.

    Returns:
        The parsed JSON content as a dictionary with the keys
        ``stations`` and ``connections``.

    Raises:
        FileNotFoundError: If the file does not exist.
        ValueError: If the JSON is malformed or does not match the expected
            structure.
    """
    path = os.fspath(path)
    try:
        with open(path, "r", encoding="utf-8") as handle:
            data = json.load(handle)
    except FileNotFoundError:
        raise FileNotFoundError(f"subway data file not found: {path}") from None
    except json.JSONDecodeError as exc:
        raise ValueError(f"invalid JSON in {path}: {exc}") from exc
    return validate_subway_data(data)


def _is_number(value) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def validate_subway_data(data) -> dict:
    """Check that ``data`` follows the subway data structure.

    Raises:
        ValueError: On the first structural problem found.
    """
    if not isinstance(data, dict):
        raise ValueError("subway data must be a JSON object")
    stations = data.get("stations")
    connections = data.get("connections")
    if not isinstance(stations, list):
        raise ValueError("'stations' must be a list")
    if not isinstance(connections, list):
        raise ValueError("'connections' must be a list")

    for index, station in enumerate(stations):
        if not isinstance(station, dict):
            raise ValueError(f"stations[{index}] must be an object")
        name = station.get("name")
        if not isinstance(name, str) or not name.strip():
            raise ValueError(f"stations[{index}].name must be a non-empty string")
        lines = station.get("lines", [])
        if not isinstance(lines, list) or not all(isinstance(x, str) for x in lines):
            raise ValueError(f"stations[{index}].lines must be a list of strings")

    for index, conn in enumerate(connections):
        if not isinstance(conn, dict):
            raise ValueError(f"connections[{index}] must be an object")
        for key in ("source", "dest", "line"):
            if not isinstance(conn.get(key), str) or not conn.get(key).strip():
                raise ValueError(f"connections[{index}].{key} must be a non-empty string")
        if not _is_number(conn.get("distance")):
            raise ValueError(f"connections[{index}].distance must be a number (meters)")
    return data


def save_subway_data(data: dict, path) -> None:
    """Write the dataset to ``path`` as UTF-8 JSON."""
    with open(os.fspath(path), "w", encoding="utf-8") as handle:
        json.dump(data, handle, ensure_ascii=False, indent=2)
        handle.write("\n")
