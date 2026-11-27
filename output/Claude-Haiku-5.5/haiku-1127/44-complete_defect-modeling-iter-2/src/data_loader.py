"""
Data loading utilities for the Beijing Subway fare calculation system.

The network data is read from ``subway_data.json`` which lives next to this
module, so the path is valid regardless of the current working directory.
"""

import json
import os

# Absolute path of the subway dataset (src/subway_data.json).
DATA_FILE_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "subway_data.json")

# Top-level keys that must be present in the dataset.
REQUIRED_KEYS = ("stations", "connections")


def load_subway_data(path=DATA_FILE_PATH):
    """
    Load the subway dataset from a JSON file.

    Args:
        path: Path to the JSON file. Defaults to ``DATA_FILE_PATH``.

    Returns:
        dict: The JSON content of the file, with keys ``stations`` and
        ``connections``.

    Raises:
        OSError: If the file cannot be opened.
        ValueError: If the JSON is malformed or required keys are missing.
    """
    with open(path, "r", encoding="utf-8") as handle:
        try:
            data = json.load(handle)
        except json.JSONDecodeError as exc:
            raise ValueError(f"malformed JSON in '{path}': {exc}") from exc

    if not isinstance(data, dict):
        raise ValueError(f"subway data in '{path}' must be a JSON object")

    for key in REQUIRED_KEYS:
        if key not in data:
            raise ValueError(f"subway data in '{path}' is missing the '{key}' key")

    return data
