"""Loading and saving of the Beijing Subway dataset (subway_data.json)."""

import json
import os

# Absolute path of the dataset file, valid regardless of the current working directory.
DATA_FILE_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "subway_data.json")


class DataLoadError(Exception):
    """Raised when the subway dataset cannot be read, parsed or has an invalid top-level structure."""


def _validate_structure(data):
    """Check that the top-level JSON structure has the expected shape.

    Args:
        data: The parsed JSON value.

    Raises:
        DataLoadError: If the structure is not an object containing list fields
            'stations' and 'connections'.
    """
    if not isinstance(data, dict):
        raise DataLoadError("top-level JSON value must be an object")
    for key in ("stations", "connections"):
        if key not in data or not isinstance(data[key], list):
            raise DataLoadError(f"missing or invalid list field '{key}'")


def load_subway_data(path):
    """Load the subway dataset from a JSON file.

    Args:
        path: Path of the JSON file.

    Returns:
        dict: The JSON content, with 'stations' and 'connections' lists.

    Raises:
        DataLoadError: If the file is missing, unreadable, not valid JSON or malformed.
    """
    try:
        with open(path, "r", encoding="utf-8") as fh:
            data = json.load(fh)
    except FileNotFoundError as exc:
        raise DataLoadError(f"subway data file not found: {path}") from exc
    except json.JSONDecodeError as exc:
        raise DataLoadError(f"subway data file is not valid JSON: {exc}") from exc
    except OSError as exc:
        raise DataLoadError(f"cannot read subway data file: {exc}") from exc
    _validate_structure(data)
    return data


def save_subway_data(data, path):
    """Write the subway dataset back to a JSON file.

    Args:
        data: The dataset dictionary.
        path: Destination file path. Parent directories are created when missing.

    Raises:
        DataLoadError: If the file cannot be written.
    """
    try:
        directory = os.path.dirname(os.path.abspath(path))
        os.makedirs(directory, exist_ok=True)
        with open(path, "w", encoding="utf-8") as fh:
            json.dump(data, fh, ensure_ascii=False, indent=2)
    except OSError as exc:
        raise DataLoadError(f"cannot write subway data file: {exc}") from exc
