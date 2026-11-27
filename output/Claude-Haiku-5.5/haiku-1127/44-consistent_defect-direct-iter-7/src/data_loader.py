"""Loading and saving of the Beijing Subway dataset (subway_data.json)."""
from __future__ import annotations

import json
import os
from typing import Any, Dict

# Absolute path of src/subway_data.json, valid regardless of the working directory.
DATA_FILE_PATH: str = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "subway_data.json"
)


def load_subway_data(path: str = DATA_FILE_PATH) -> Dict[str, Any]:
    """Load the subway dataset and return its JSON content as a dictionary.

    Raises:
        OSError: if the file cannot be read.
        ValueError: if the JSON content does not have the expected structure.
    """
    with open(path, "r", encoding="utf-8") as handle:
        data = json.load(handle)

    if not isinstance(data, dict):
        raise ValueError("subway data must be a JSON object")
    for key in ("stations", "connections"):
        if not isinstance(data.get(key), list):
            raise ValueError(f"subway data is missing the '{key}' list")
    return data


def save_subway_data(data: Dict[str, Any], path: str = DATA_FILE_PATH) -> None:
    """Write the dataset dictionary back to a JSON file."""
    with open(path, "w", encoding="utf-8") as handle:
        json.dump(data, handle, ensure_ascii=False, indent=2)
        handle.write("\n")
