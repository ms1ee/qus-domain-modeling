"""Data loading utilities for the Beijing Subway fare calculation system.

The network data lives in ``subway_data.json`` next to this module.  The
path is computed from this file's location so it is valid regardless of
the current working directory.
"""

import json
import os

DATA_FILE_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "subway_data.json")


def load_subway_data(path=DATA_FILE_PATH):
    """Load and return the JSON content of the subway data file.

    Raises:
        FileNotFoundError: if the file does not exist.
        ValueError: if the file content is not valid JSON or is malformed.
    """
    if path is None:
        path = DATA_FILE_PATH
    if not os.path.exists(path):
        raise FileNotFoundError(f"Subway data file not found: {path}")
    with open(path, "r", encoding="utf-8") as f:
        try:
            data = json.load(f)
        except json.JSONDecodeError as exc:
            raise ValueError(f"Invalid JSON in subway data file: {exc}") from exc
    if not isinstance(data, dict):
        raise ValueError("Subway data file must contain a JSON object")
    data.setdefault("stations", [])
    data.setdefault("connections", [])
    return data


def save_subway_data(data, path=DATA_FILE_PATH):
    """Write the subway data back to a JSON file."""
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
