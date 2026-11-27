"""
Data loading utilities for the Beijing Subway network.

The network dataset is stored in ``subway_data.json`` located in the same
directory as this module, so it can be found regardless of the working
directory the program is started from.
"""

import json
import os

# Absolute path of the bundled subway dataset (src/subway_data.json).
DATA_FILE_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "subway_data.json")


def load_subway_data(path=DATA_FILE_PATH):
    """Load and minimally validate the subway dataset.

    Args:
        path: Path to the JSON file. Defaults to DATA_FILE_PATH.

    Returns:
        dict: The JSON content with at least the keys "stations" and "connections".

    Raises:
        OSError: If the file cannot be read.
        ValueError: If the JSON is malformed or lacks the required structure.
    """
    if path is None:
        path = DATA_FILE_PATH
    with open(path, "r", encoding="utf-8") as handle:
        data = json.load(handle)

    if not isinstance(data, dict):
        raise ValueError("Subway data must be a JSON object")
    if not isinstance(data.get("stations"), list):
        raise ValueError("Subway data must contain a 'stations' list")
    if not isinstance(data.get("connections"), list):
        raise ValueError("Subway data must contain a 'connections' list")
    return data
