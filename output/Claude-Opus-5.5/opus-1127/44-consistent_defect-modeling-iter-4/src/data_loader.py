"""
Data loading utilities for the Beijing Subway fare calculation system.

The subway network data lives in ``subway_data.json`` next to this module.
``DATA_FILE_PATH`` is an absolute path so it is valid from any working
directory.
"""

import json
import os

# Absolute path of src/subway_data.json (independent of the working directory).
DATA_FILE_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "subway_data.json")


def load_subway_data(path=DATA_FILE_PATH):
    """Load and return the JSON content of the subway data file.

    :param path: path of the JSON data file (defaults to DATA_FILE_PATH)
    :return: dict with keys "stations" and "connections"
    :raises FileNotFoundError: if the file does not exist
    :raises ValueError: if the file is not valid JSON
    """
    if path is None:
        path = DATA_FILE_PATH
    with open(path, "r", encoding="utf-8") as fh:
        try:
            data = json.load(fh)
        except json.JSONDecodeError as exc:
            raise ValueError(f"Invalid subway data file '{path}': {exc}") from exc
    if not isinstance(data, dict):
        raise ValueError(f"Invalid subway data file '{path}': top-level object must be a dict")
    data.setdefault("stations", [])
    data.setdefault("connections", [])
    return data


def save_subway_data(data, path=DATA_FILE_PATH):
    """Write subway data back to a JSON file."""
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(data, fh, ensure_ascii=False, indent=2)
