"""
Data loading utilities for the Beijing Subway fare calculation system.

The subway network data lives in ``subway_data.json`` next to this module.
``DATA_FILE_PATH`` is an absolute path, so it is valid from any working
directory.
"""

import json
import os

DATA_FILE_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "subway_data.json")


def load_subway_data(path=DATA_FILE_PATH):
    """Load and return the JSON content of the subway data file.

    :param path: path to the JSON data file (defaults to DATA_FILE_PATH)
    :return: dict with keys ``stations`` and ``connections``
    :raises FileNotFoundError: if the file does not exist
    :raises ValueError: if the file is not valid JSON or has a wrong structure
    """
    if path is None:
        path = DATA_FILE_PATH
    if not os.path.isfile(path):
        raise FileNotFoundError(f"Subway data file not found: {path}")
    try:
        with open(path, "r", encoding="utf-8") as fh:
            data = json.load(fh)
    except json.JSONDecodeError as exc:
        raise ValueError(f"Subway data file is not valid JSON: {exc}") from exc
    if not isinstance(data, dict):
        raise ValueError("Subway data must be a JSON object")
    data.setdefault("stations", [])
    data.setdefault("connections", [])
    return data


def save_subway_data(data, path=DATA_FILE_PATH):
    """Write subway data back to a JSON file."""
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(data, fh, ensure_ascii=False, indent=2)
