"""Loading and saving of the Beijing Subway dataset (subway_data.json).

The dataset has the form:
    {"stations": [{"name": str, "lines": [str]}],
     "connections": [{"source": str, "dest": str, "distance": int, "line": str}]}
"""

import json
import os

# Absolute path of src/subway_data.json, valid regardless of the working directory.
DATA_FILE_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "subway_data.json")


class DataLoadError(Exception):
    """Raised when the subway dataset cannot be read or is malformed."""


def validate_subway_data(data):
    """Check the top-level structure of a subway dataset.

    Args:
        data: The parsed JSON object.

    Returns:
        The same data object when it is structurally valid.

    Raises:
        DataLoadError: If the structure is invalid.
    """
    if not isinstance(data, dict):
        raise DataLoadError("Subway data must be a JSON object")
    for key in ("stations", "connections"):
        if not isinstance(data.get(key), list):
            raise DataLoadError(f"Subway data field '{key}' must be a list")
    return data


def load_subway_data(path=DATA_FILE_PATH):
    """Load the subway dataset from a JSON file.

    Args:
        path: Path to the JSON file. Defaults to src/subway_data.json.

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
        raise DataLoadError(f"Subway data file is not valid JSON: {exc}") from exc
    except OSError as exc:
        raise DataLoadError(f"Cannot read subway data file: {exc}") from exc
    return validate_subway_data(data)


def save_subway_data(data, path=DATA_FILE_PATH):
    """Write the subway dataset back to a JSON file.

    Args:
        data: The dataset dictionary.
        path: Destination file path.

    Raises:
        DataLoadError: If the file cannot be written.
    """
    validate_subway_data(data)
    try:
        with open(path, "w", encoding="utf-8") as handle:
            json.dump(data, handle, ensure_ascii=False, indent=2)
    except OSError as exc:
        raise DataLoadError(f"Cannot write subway data file: {exc}") from exc
