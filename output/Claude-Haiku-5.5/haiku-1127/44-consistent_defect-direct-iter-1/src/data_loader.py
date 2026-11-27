"""Loading and validation of the Beijing Subway data file.

The data file is ``subway_data.json`` located next to this module, so the
program can be started from any working directory.
"""

import json
import os

_THIS_DIR = os.path.dirname(os.path.abspath(__file__))

# Absolute path of src/subway_data.json, valid from any working directory.
DATA_FILE_PATH = os.path.join(_THIS_DIR, "subway_data.json")


class DataLoadError(Exception):
    """Raised when the subway data file cannot be read or is malformed."""


def _require(condition, message):
    """Raise DataLoadError with ``message`` when ``condition`` is false."""
    if not condition:
        raise DataLoadError(message)


def _validate(data):
    """Check that ``data`` follows the documented JSON schema.

    Expected schema::

        {"stations": [{"name": str, "lines": [str]}],
         "connections": [{"source": str, "dest": str,
                          "distance": int, "line": str}]}
    """
    _require(isinstance(data, dict), "Subway data must be a JSON object")
    stations = data.get("stations")
    connections = data.get("connections")
    _require(isinstance(stations, list), "'stations' must be a list")
    _require(isinstance(connections, list), "'connections' must be a list")

    for index, station in enumerate(stations):
        _require(isinstance(station, dict),
                 f"Station #{index} must be an object")
        name = station.get("name")
        _require(isinstance(name, str) and name.strip(),
                 f"Station #{index} has an invalid 'name'")
        lines = station.get("lines", [])
        _require(isinstance(lines, list) and all(isinstance(x, str) for x in lines),
                 f"Station '{name}' has an invalid 'lines' value")

    for index, conn in enumerate(connections):
        _require(isinstance(conn, dict),
                 f"Connection #{index} must be an object")
        for key in ("source", "dest", "line"):
            _require(isinstance(conn.get(key), str),
                     f"Connection #{index} has an invalid '{key}'")
        distance = conn.get("distance")
        _require(isinstance(distance, (int, float)) and not isinstance(distance, bool),
                 f"Connection #{index} has an invalid 'distance'")


def load_subway_data(path):
    """Load and validate the subway data file.

    Args:
        path: Path of the JSON data file.

    Returns:
        dict: The JSON content of the file.

    Raises:
        DataLoadError: If the file is missing, unreadable, not valid JSON,
            or does not follow the expected schema.
    """
    try:
        with open(path, "r", encoding="utf-8") as handle:
            data = json.load(handle)
    except FileNotFoundError as exc:
        raise DataLoadError(f"Subway data file not found: {path}") from exc
    except json.JSONDecodeError as exc:
        raise DataLoadError(f"Subway data file is not valid JSON: {exc}") from exc
    except OSError as exc:
        raise DataLoadError(f"Cannot read subway data file: {exc}") from exc

    _validate(data)
    return data
