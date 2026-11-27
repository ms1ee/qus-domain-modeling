"""Loading and saving of the Beijing Subway network dataset (subway_data.json)."""
from __future__ import annotations

import json
import os
from typing import Any, Dict

# Absolute path of subway_data.json, valid regardless of the current working directory.
DATA_FILE_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "subway_data.json")


class DataLoadError(Exception):
    """Raised when the subway dataset cannot be read or is malformed."""


def load_subway_data(path: str = DATA_FILE_PATH) -> Dict[str, Any]:
    """Load the subway dataset JSON file and return its content as a dict.

    The returned dict always contains the keys "stations" and "connections"
    (defaulting to empty lists when absent).
    """
    try:
        with open(path, "r", encoding="utf-8") as handle:
            data = json.load(handle)
    except FileNotFoundError as exc:
        raise DataLoadError(f"subway data file not found: {path}") from exc
    except json.JSONDecodeError as exc:
        raise DataLoadError(f"subway data file is not valid JSON: {path} ({exc})") from exc
    except OSError as exc:
        raise DataLoadError(f"cannot read subway data file: {path} ({exc})") from exc

    if not isinstance(data, dict):
        raise DataLoadError("subway data must be a JSON object")
    data.setdefault("stations", [])
    data.setdefault("connections", [])
    return data


def save_subway_data(data: Dict[str, Any], path: str = DATA_FILE_PATH) -> None:
    """Write the subway dataset dict back to a JSON file."""
    directory = os.path.dirname(os.path.abspath(path))
    os.makedirs(directory, exist_ok=True)
    try:
        with open(path, "w", encoding="utf-8") as handle:
            json.dump(data, handle, ensure_ascii=False, indent=2)
            handle.write("\n")
    except OSError as exc:
        raise DataLoadError(f"cannot write subway data file: {path} ({exc})") from exc
