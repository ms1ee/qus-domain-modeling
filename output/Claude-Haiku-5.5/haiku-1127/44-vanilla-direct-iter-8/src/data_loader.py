"""Loading of the Beijing Subway network dataset (subway_data.json)."""

import json
import os

from errors import DataLoadError

_SRC_DIR = os.path.dirname(os.path.abspath(__file__))

# Absolute path of src/subway_data.json, valid regardless of the working directory.
DATA_FILE_PATH = os.path.join(_SRC_DIR, "subway_data.json")


def load_subway_data(path=DATA_FILE_PATH):
    """Load the subway dataset from a JSON file.

    Args:
        path: Path of the JSON file. Defaults to DATA_FILE_PATH.

    Returns:
        dict: The JSON content, with the keys "stations" and "connections".

    Raises:
        DataLoadError: If the file is missing, malformed, or lacks required keys.
    """
    if path is None:
        path = DATA_FILE_PATH
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
    for key in ("stations", "connections"):
        if key not in data or not isinstance(data[key], list):
            raise DataLoadError(f"Subway data is missing the list field '{key}'")
    return data
