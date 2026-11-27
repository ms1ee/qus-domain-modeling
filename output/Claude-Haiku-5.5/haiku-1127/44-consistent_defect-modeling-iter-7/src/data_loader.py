"""
Data loading utilities for the Beijing Subway network.

The network dataset lives in ``subway_data.json`` located next to this file.
Its structure is:

    {"stations": [{"name": str, "lines": [str]}],
     "connections": [{"source": str, "dest": str, "distance": int, "line": str}]}
"""

import json
import os

# Absolute path of the data file, valid regardless of the current working directory.
DATA_FILE_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "subway_data.json")


def load_subway_data(path=DATA_FILE_PATH):
    """Load the subway dataset from a JSON file.

    Args:
        path: Path to the JSON file (defaults to DATA_FILE_PATH).

    Returns:
        dict: The JSON content, always containing "stations" and "connections" lists.

    Raises:
        OSError: If the file cannot be read.
        ValueError: If the JSON content is not an object or is malformed.
    """
    with open(path, "r", encoding="utf-8") as handle:
        data = json.load(handle)
    if not isinstance(data, dict):
        raise ValueError("Subway data file must contain a JSON object")
    data.setdefault("stations", [])
    data.setdefault("connections", [])
    return data


def save_subway_data(data, path=DATA_FILE_PATH):
    """Write the subway dataset back to a JSON file.

    Args:
        data: The dataset dictionary.
        path: Destination file path.

    Raises:
        OSError: If the file cannot be written.
    """
    with open(path, "w", encoding="utf-8") as handle:
        json.dump(data, handle, ensure_ascii=False, indent=2)
