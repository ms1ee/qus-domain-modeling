"""Loading and saving of the Beijing Subway data file."""

from __future__ import annotations

import json
import os
from typing import Any, Dict

from errors import DataError

DATA_FILE_PATH: str = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "subway_data.json"
)


def load_subway_data(path: str) -> Dict[str, Any]:
    """Load the subway data JSON file and return its content as a dictionary.

    Raises:
        OSError: if the file cannot be read.
        DataError: if the JSON structure is not the expected one.
    """
    with open(path, "r", encoding="utf-8") as handle:
        data = json.load(handle)

    if not isinstance(data, dict):
        raise DataError("subway data root must be a JSON object")
    if not isinstance(data.get("stations"), list):
        raise DataError("subway data must contain a 'stations' list")
    if not isinstance(data.get("connections"), list):
        raise DataError("subway data must contain a 'connections' list")
    return data


def save_subway_data(data: Dict[str, Any], path: str = DATA_FILE_PATH) -> None:
    """Write subway data back to a JSON file (UTF-8, pretty-printed)."""
    with open(path, "w", encoding="utf-8") as handle:
        json.dump(data, handle, ensure_ascii=False, indent=2)
        handle.write("\n")
