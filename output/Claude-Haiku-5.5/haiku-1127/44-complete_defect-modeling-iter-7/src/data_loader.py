"""Loading and saving of the Beijing Subway network dataset.

The dataset is stored in ``subway_data.json`` next to this module and has the form::

    {"stations": [{"name": str, "lines": [str]}],
     "connections": [{"source": str, "dest": str, "distance": int, "line": str}]}
"""

from __future__ import annotations

import json
import os
from typing import Any

# Absolute path of the dataset, valid regardless of the current working directory.
DATA_FILE_PATH: str = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "subway_data.json"
)


class DataLoadError(Exception):
    """Raised when the subway dataset cannot be read or has an invalid structure."""


def _validate_structure(data: Any) -> None:
    """Check the top-level structure of the dataset.

    Raises:
        DataLoadError: if the structure does not match the expected format.
    """
    if not isinstance(data, dict):
        raise DataLoadError("top-level JSON value must be an object")
    for key in ("stations", "connections"):
        if not isinstance(data.get(key), list):
            raise DataLoadError(f"'{key}' must be a list")


def load_subway_data(path: str = DATA_FILE_PATH) -> dict:
    """Load the subway dataset from a JSON file.

    Args:
        path: path of the JSON file (defaults to src/subway_data.json).

    Returns:
        The parsed JSON content as a dictionary.

    Raises:
        DataLoadError: if the file is missing, unreadable, not JSON, or malformed.
    """
    try:
        with open(path, "r", encoding="utf-8") as handle:
            data = json.load(handle)
    except FileNotFoundError as exc:
        raise DataLoadError(f"subway data file not found: {path}") from exc
    except json.JSONDecodeError as exc:
        raise DataLoadError(f"subway data file is not valid JSON: {exc}") from exc
    except OSError as exc:
        raise DataLoadError(f"cannot read subway data file: {exc}") from exc

    _validate_structure(data)
    return data


def save_subway_data(data: dict, path: str = DATA_FILE_PATH) -> None:
    """Persist a dataset dictionary to a JSON file.

    Args:
        data: dataset with 'stations' and 'connections' lists.
        path: destination file path.

    Raises:
        DataLoadError: if the data is malformed or cannot be written.
    """
    _validate_structure(data)
    try:
        with open(path, "w", encoding="utf-8") as handle:
            json.dump(data, handle, ensure_ascii=False, indent=2)
    except OSError as exc:
        raise DataLoadError(f"cannot write subway data file: {exc}") from exc
