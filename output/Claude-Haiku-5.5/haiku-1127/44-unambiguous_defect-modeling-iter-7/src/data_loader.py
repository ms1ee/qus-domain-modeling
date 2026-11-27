"""
Data loading utilities for the Beijing Subway network.

The raw network dataset lives in ``subway_data.json`` next to this module.
``DATA_FILE_PATH`` is resolved from the location of this file, so it is valid
regardless of the current working directory.
"""

import json
import os

_THIS_DIR = os.path.dirname(os.path.abspath(__file__))

# Absolute path of the subway dataset (src/subway_data.json).
DATA_FILE_PATH = os.path.join(_THIS_DIR, "subway_data.json")


def load_subway_data(path=DATA_FILE_PATH):
    """
    Load the subway network dataset from a JSON file.

    Args:
        path: Path of the JSON file. Defaults to ``DATA_FILE_PATH``.

    Returns:
        dict: The JSON content, with the keys ``stations`` and ``connections``.

    Raises:
        OSError: If the file cannot be read.
        ValueError: If the JSON is malformed or has an unexpected top-level type.
    """
    with open(path, "r", encoding="utf-8") as fh:
        data = json.load(fh)
    if not isinstance(data, dict):
        raise ValueError("Subway data must be a JSON object")
    return data
