"""Data loading utilities for the Beijing Subway fare calculation system.

The network data lives in ``subway_data.json`` next to this module.  The
path is computed from this file's location, so it is valid no matter what
the current working directory is.
"""

import json
import os

#: Absolute path of the bundled subway data file (src/subway_data.json).
DATA_FILE_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "subway_data.json")


def load_subway_data(path=DATA_FILE_PATH):
    """Load and return the JSON content of the subway data file.

    :param path: path of the JSON file (defaults to :data:`DATA_FILE_PATH`).
    :return: dict with keys ``stations`` and ``connections``.
    :raises FileNotFoundError: if the file does not exist.
    :raises ValueError: if the file is not valid JSON.
    """
    if path is None:
        path = DATA_FILE_PATH
    with open(path, "r", encoding="utf-8") as fh:
        try:
            data = json.load(fh)
        except json.JSONDecodeError as exc:
            raise ValueError(f"Invalid JSON in data file '{path}': {exc}") from exc
    if not isinstance(data, dict):
        raise ValueError(f"Data file '{path}' must contain a JSON object")
    data.setdefault("stations", [])
    data.setdefault("connections", [])
    return data
