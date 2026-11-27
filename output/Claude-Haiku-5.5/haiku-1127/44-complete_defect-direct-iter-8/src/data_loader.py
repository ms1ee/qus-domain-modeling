"""Loading of the Beijing Subway network dataset from subway_data.json."""

import json
import os

from errors import DataError

# Absolute path of src/subway_data.json, valid regardless of the working directory.
DATA_FILE_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "subway_data.json")


def load_subway_data(path=DATA_FILE_PATH):
    """Load the subway network JSON file and return its content as a dictionary.

    Args:
        path: Path of the JSON data file.

    Returns:
        dict with keys "stations" (list of {"name", "lines"}) and
        "connections" (list of {"source", "dest", "distance", "line"}).

    Raises:
        DataError: If the file is missing, is not valid JSON, or lacks the
            expected structure.
    """
    try:
        with open(path, "r", encoding="utf-8") as handle:
            data = json.load(handle)
    except FileNotFoundError as exc:
        raise DataError(f"Subway data file not found: {path}") from exc
    except json.JSONDecodeError as exc:
        raise DataError(f"Subway data file is not valid JSON: {path} ({exc})") from exc

    if not isinstance(data, dict):
        raise DataError("Subway data root must be a JSON object")
    if not isinstance(data.get("stations"), list):
        raise DataError("Subway data must contain a 'stations' list")
    if not isinstance(data.get("connections"), list):
        raise DataError("Subway data must contain a 'connections' list")
    return data
