"""Data loading utilities for the Beijing Subway network.

The subway network dataset lives in ``subway_data.json`` next to this module.
``DATA_FILE_PATH`` is resolved relative to this file so that the program can be
started from any working directory.
"""

import json
import os

# Absolute path of src/subway_data.json, independent of the current working directory.
DATA_FILE_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "subway_data.json")

# Top-level keys that every dataset file must provide as lists.
_REQUIRED_LIST_KEYS = ("stations", "connections")


def load_subway_data(path=DATA_FILE_PATH) -> dict:
    """Load and minimally validate the subway dataset.

    Args:
        path: Location of the JSON dataset file.

    Returns:
        The parsed JSON content as a dictionary.

    Raises:
        OSError: If the file cannot be opened.
        ValueError: If the JSON is invalid or lacks the required structure.
    """
    path = os.fspath(path)
    with open(path, "r", encoding="utf-8") as handle:
        try:
            data = json.load(handle)
        except json.JSONDecodeError as exc:
            raise ValueError(f"invalid JSON in '{path}': {exc}") from exc

    if not isinstance(data, dict):
        raise ValueError(f"dataset '{path}' must contain a JSON object at the top level")

    for key in _REQUIRED_LIST_KEYS:
        if key not in data or not isinstance(data[key], list):
            raise ValueError(f"dataset '{path}' must contain a list under key '{key}'")

    return data
