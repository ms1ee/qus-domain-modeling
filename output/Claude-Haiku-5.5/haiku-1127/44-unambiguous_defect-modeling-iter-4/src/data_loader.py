"""Loading of the Beijing Subway network dataset from subway_data.json.

The data file is located relative to this module, so the program works from
any current working directory.
"""
import json
import os

from errors import DataLoadError

_MODULE_DIR = os.path.dirname(os.path.abspath(__file__))

# Absolute path of src/subway_data.json, valid from any working directory.
DATA_FILE_PATH = os.path.join(_MODULE_DIR, "subway_data.json")


def load_subway_data(path):
    """Load and structurally validate the subway dataset.

    Args:
        path: path of the JSON file to read.

    Returns:
        dict with the JSON content, containing "stations" and "connections".

    Raises:
        DataLoadError: if the file cannot be read, is not valid JSON, or does
            not match the expected structure.
    """
    try:
        with open(path, "r", encoding="utf-8") as handle:
            data = json.load(handle)
    except FileNotFoundError as exc:
        raise DataLoadError("Subway data file not found: {}".format(path)) from exc
    except json.JSONDecodeError as exc:
        raise DataLoadError(
            "Subway data file is not valid JSON ({}): {}".format(path, exc)
        ) from exc
    except OSError as exc:
        raise DataLoadError("Cannot read subway data file ({}): {}".format(path, exc)) from exc

    _validate_structure(data)
    return data


def _is_number(value):
    """Return True for int/float values, excluding booleans."""
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def _validate_structure(data):
    """Check the top-level structure and the fields of every entry.

    Raises:
        DataLoadError: on the first structural problem found.
    """
    if not isinstance(data, dict):
        raise DataLoadError("Subway data must be a JSON object")

    stations = data.get("stations")
    connections = data.get("connections")
    if not isinstance(stations, list) or not isinstance(connections, list):
        raise DataLoadError("Subway data must contain 'stations' and 'connections' lists")

    for index, station in enumerate(stations):
        if not isinstance(station, dict):
            raise DataLoadError("Station entry #{} is not an object".format(index))
        name = station.get("name")
        if not isinstance(name, str) or not name.strip():
            raise DataLoadError("Station entry #{} has an invalid 'name'".format(index))
        lines = station.get("lines", [])
        if not isinstance(lines, list) or not all(isinstance(item, str) for item in lines):
            raise DataLoadError("Station '{}' has an invalid 'lines' list".format(name))

    for index, connection in enumerate(connections):
        if not isinstance(connection, dict):
            raise DataLoadError("Connection entry #{} is not an object".format(index))
        for key in ("source", "dest", "line"):
            value = connection.get(key)
            if not isinstance(value, str) or not value.strip():
                raise DataLoadError(
                    "Connection entry #{} has an invalid '{}'".format(index, key)
                )
        if not _is_number(connection.get("distance")):
            raise DataLoadError(
                "Connection entry #{} has an invalid 'distance'".format(index)
            )
