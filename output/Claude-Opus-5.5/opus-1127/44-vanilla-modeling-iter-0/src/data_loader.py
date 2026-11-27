"""
Data loading utilities for the Beijing Subway fare calculation system.

The subway network data lives in ``subway_data.json`` next to this module.
``DATA_FILE_PATH`` is computed from this file's location, so it is valid
regardless of the current working directory.
"""

import json
import os

#: Absolute path of the bundled subway network data file.
DATA_FILE_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "subway_data.json")


def load_subway_data(path=DATA_FILE_PATH):
    """Load and return the JSON content of the subway data file.

    :param path: path of the JSON data file (defaults to ``DATA_FILE_PATH``)
    :return: the parsed JSON content (a dict with ``stations`` and ``connections``)
    :raises FileNotFoundError: if the file does not exist
    :raises ValueError: if the file is not valid JSON
    """
    if path is None:
        path = DATA_FILE_PATH
    with open(path, "r", encoding="utf-8") as fh:
        try:
            data = json.load(fh)
        except json.JSONDecodeError as exc:
            raise ValueError(f"Invalid JSON in subway data file '{path}': {exc}") from exc
    return data
