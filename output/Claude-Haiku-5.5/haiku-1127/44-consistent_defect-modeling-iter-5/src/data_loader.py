"""Loading and saving of the Beijing Subway dataset stored in subway_data.json."""

import json
import os

from subway_errors import DataError

# Absolute path of src/subway_data.json, valid regardless of the current working directory.
DATA_FILE_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "subway_data.json")


def load_subway_data(path=DATA_FILE_PATH):
    """Load the subway dataset from a JSON file.

    Args:
        path: Path of the JSON file. Defaults to DATA_FILE_PATH.

    Returns:
        dict: The JSON content of the file, with keys "stations" and "connections".

    Raises:
        DataError: If the file is missing, not valid JSON, or structurally malformed.
    """
    try:
        with open(path, "r", encoding="utf-8") as fh:
            data = json.load(fh)
    except FileNotFoundError as exc:
        raise DataError(f"Subway data file not found: {path}") from exc
    except json.JSONDecodeError as exc:
        raise DataError(f"Subway data file is not valid JSON: {path} ({exc})") from exc
    except OSError as exc:
        raise DataError(f"Cannot read subway data file: {path} ({exc})") from exc

    if not isinstance(data, dict):
        raise DataError("Subway data root must be a JSON object")
    for key in ("stations", "connections"):
        if key not in data:
            raise DataError(f"Subway data is missing the '{key}' section")
        if not isinstance(data[key], list):
            raise DataError(f"Subway data section '{key}' must be a list")
    return data


def save_subway_data(data, path=DATA_FILE_PATH):
    """Write the subway dataset back to a JSON file.

    Args:
        data: The dataset dictionary.
        path: Destination file path.

    Raises:
        DataError: If the file cannot be written.
    """
    try:
        with open(path, "w", encoding="utf-8") as fh:
            json.dump(data, fh, ensure_ascii=False, indent=2)
    except OSError as exc:
        raise DataError(f"Cannot write subway data file: {path} ({exc})") from exc
