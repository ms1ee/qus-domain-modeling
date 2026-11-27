"""Loading and saving of the Beijing Subway network dataset.

The dataset is a JSON document with two top-level arrays:

    {"stations": [{"name": str, "lines": [str]}],
     "connections": [{"source": str, "dest": str, "distance": int, "line": str}]}

Distances are expressed in meters.
"""

import json
import os
from typing import Any, Dict

# Absolute path of subway_data.json, valid regardless of the working directory.
DATA_FILE_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "subway_data.json")


def load_subway_data(path: str) -> Dict[str, Any]:
    """Load the subway dataset from a JSON file.

    Args:
        path: Path of the JSON file to read.

    Returns:
        The parsed JSON content as a dictionary.

    Raises:
        OSError: If the file cannot be read.
        ValueError: If the content is not a valid subway dataset.
    """
    with open(path, "r", encoding="utf-8") as handle:
        data = json.load(handle)

    if not isinstance(data, dict):
        raise ValueError(f"Subway data file '{path}' must contain a JSON object")
    for key in ("stations", "connections"):
        if key not in data:
            raise ValueError(f"Subway data file '{path}' is missing the '{key}' array")
        if not isinstance(data[key], list):
            raise ValueError(f"'{key}' in subway data file '{path}' must be an array")
    return data


def save_subway_data(data: Dict[str, Any], path: str) -> None:
    """Write the subway dataset back to a JSON file.

    Args:
        data: Dataset dictionary with 'stations' and 'connections' arrays.
        path: Destination file path.

    Raises:
        OSError: If the file cannot be written.
    """
    with open(path, "w", encoding="utf-8") as handle:
        json.dump(data, handle, ensure_ascii=False, indent=2)
        handle.write("\n")
