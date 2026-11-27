"""Loads the raw Beijing Subway network dataset from subway_data.json.

The JSON file has the structure:
    {"stations": [{"name": str, "lines": [str]}],
     "connections": [{"source": str, "dest": str, "distance": int, "line": str}]}
"""

import json
import os

# Absolute path of src/subway_data.json, valid from any working directory.
DATA_FILE_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "subway_data.json")


class DataLoadError(Exception):
    """Raised when the subway dataset cannot be read or has an invalid structure."""


def load_subway_data(path=None):
    """Read the subway dataset and return its JSON content as a dictionary.

    Args:
        path: Optional path to a JSON file. Defaults to DATA_FILE_PATH.

    Returns:
        dict with keys "stations" and "connections".

    Raises:
        DataLoadError: if the file is missing, malformed or lacks required keys.
    """
    file_path = DATA_FILE_PATH if path is None else path
    try:
        with open(file_path, "r", encoding="utf-8") as handle:
            data = json.load(handle)
    except FileNotFoundError as exc:
        raise DataLoadError(f"Subway data file not found: {file_path}") from exc
    except json.JSONDecodeError as exc:
        raise DataLoadError(f"Subway data file is not valid JSON: {exc}") from exc
    except OSError as exc:
        raise DataLoadError(f"Cannot read subway data file: {exc}") from exc

    if not isinstance(data, dict):
        raise DataLoadError("Subway data root must be a JSON object")
    for key in ("stations", "connections"):
        if key not in data or not isinstance(data[key], list):
            raise DataLoadError(f"Subway data is missing list field '{key}'")
    return data
