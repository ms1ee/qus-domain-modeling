"""Data loading utilities for the Beijing Subway dataset.

The dataset lives in ``subway_data.json`` next to this module. The file has the
form::

    {"stations": [{"name": str, "lines": [str]}],
     "connections": [{"source": str, "dest": str, "distance": int, "line": str}]}

Distances are expressed in meters.
"""

import json
import os

# Absolute path of src/subway_data.json, valid regardless of the working directory.
DATA_FILE_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "subway_data.json")


class DataLoadError(Exception):
    """Raised when the subway dataset cannot be read or has an invalid structure."""


def _validate_structure(data):
    """Check that the top-level structure of the dataset is usable.

    Detailed content checks (distances, line consistency, ...) are performed
    later by the data integrity module.
    """
    if not isinstance(data, dict):
        raise DataLoadError("Dataset root must be a JSON object")
    for key in ("stations", "connections"):
        if key not in data:
            raise DataLoadError(f"Dataset is missing the '{key}' section")
        if not isinstance(data[key], list):
            raise DataLoadError(f"Dataset section '{key}' must be a list")


def load_subway_data(path=DATA_FILE_PATH) -> dict:
    """Load and return the JSON content of the subway dataset.

    Args:
        path: Path of the JSON file. Defaults to ``src/subway_data.json``.

    Returns:
        The parsed dataset as a dictionary.

    Raises:
        DataLoadError: If the file is missing, unreadable, or malformed.
    """
    path = os.fspath(path)
    try:
        with open(path, "r", encoding="utf-8") as handle:
            data = json.load(handle)
    except FileNotFoundError as exc:
        raise DataLoadError(f"Data file not found: {path}") from exc
    except json.JSONDecodeError as exc:
        raise DataLoadError(f"Data file is not valid JSON: {exc}") from exc
    except OSError as exc:
        raise DataLoadError(f"Unable to read data file: {exc}") from exc

    _validate_structure(data)
    return data


def save_subway_data(data, path=DATA_FILE_PATH) -> None:
    """Write the dataset dictionary back to a JSON file.

    Args:
        data: Dataset dictionary in the same format returned by ``load_subway_data``.
        path: Destination file path.

    Raises:
        DataLoadError: If the file cannot be written.
    """
    path = os.fspath(path)
    try:
        with open(path, "w", encoding="utf-8") as handle:
            json.dump(data, handle, ensure_ascii=False, indent=2)
            handle.write("\n")
    except OSError as exc:
        raise DataLoadError(f"Unable to write data file: {exc}") from exc
