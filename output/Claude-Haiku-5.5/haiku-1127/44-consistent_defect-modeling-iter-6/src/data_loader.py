"""
Data loading utilities for the Beijing Subway network.

Provides the location of the bundled dataset (subway_data.json) and helpers
to load and persist its JSON content.
"""

import json
import os
from typing import Any, Dict

# Absolute path of src/subway_data.json, valid regardless of the working directory.
DATA_FILE_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "subway_data.json")

# Top-level keys that every dataset file must contain.
REQUIRED_KEYS = ("stations", "connections")


def load_subway_data(path: str = DATA_FILE_PATH) -> Dict[str, Any]:
    """Load the subway dataset from a JSON file.

    Args:
        path: Path of the JSON file to read.

    Returns:
        The parsed JSON content as a dictionary.

    Raises:
        OSError: If the file cannot be read.
        ValueError: If the JSON is malformed or lacks required keys.
    """
    file_path = os.fspath(path)
    with open(file_path, "r", encoding="utf-8") as fh:
        data = json.load(fh)

    if not isinstance(data, dict):
        raise ValueError(f"Subway data in '{file_path}' must be a JSON object")

    for key in REQUIRED_KEYS:
        if key not in data:
            raise ValueError(f"Missing key '{key}' in subway data file '{file_path}'")
        if not isinstance(data[key], list):
            raise ValueError(f"Key '{key}' in '{file_path}' must be a JSON array")

    return data


def save_subway_data(data: Dict[str, Any], path: str = DATA_FILE_PATH) -> None:
    """Persist the subway dataset to a JSON file.

    Args:
        data: Dataset dictionary with 'stations' and 'connections' keys.
        path: Destination file path.
    """
    with open(os.fspath(path), "w", encoding="utf-8") as fh:
        json.dump(data, fh, ensure_ascii=False, indent=2)
        fh.write("\n")
