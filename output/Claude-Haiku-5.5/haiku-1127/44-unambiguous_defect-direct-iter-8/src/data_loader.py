"""Loading of the Beijing Subway network dataset from the JSON data file."""

import json
import os

from errors import DataError

# Absolute path of src/subway_data.json, independent of the current working directory.
DATA_FILE_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "subway_data.json")


def load_subway_data(path=None):
    """Load and validate the subway dataset.

    Args:
        path: Optional path of a JSON file. Defaults to DATA_FILE_PATH.

    Returns:
        dict: The JSON content with "stations" and "connections" lists.

    Raises:
        DataError: If the file cannot be read, is not valid JSON, or has
            an unexpected structure.
    """
    file_path = DATA_FILE_PATH if path is None else path
    try:
        with open(file_path, "r", encoding="utf-8") as handle:
            data = json.load(handle)
    except FileNotFoundError as exc:
        raise DataError(f"subway data file not found: {file_path}") from exc
    except json.JSONDecodeError as exc:
        raise DataError(f"subway data file is not valid JSON: {exc}") from exc
    except OSError as exc:
        raise DataError(f"cannot read subway data file: {exc}") from exc
    _validate(data)
    return data


def _validate(data):
    """Check the top-level structure of the dataset."""
    if not isinstance(data, dict):
        raise DataError("top-level JSON value must be an object")
    stations = data.get("stations")
    connections = data.get("connections")
    if not isinstance(stations, list) or not isinstance(connections, list):
        raise DataError("'stations' and 'connections' must both be lists")
    for index, record in enumerate(stations):
        if not isinstance(record, dict) or not isinstance(record.get("name"), str):
            raise DataError(f"malformed station record at index {index}")
        if not isinstance(record.get("lines", []), list):
            raise DataError(f"'lines' of station record at index {index} must be a list")
    for index, conn in enumerate(connections):
        if not isinstance(conn, dict) or not all(
            key in conn for key in ("source", "dest", "distance", "line")
        ):
            raise DataError(f"malformed connection record at index {index}")
