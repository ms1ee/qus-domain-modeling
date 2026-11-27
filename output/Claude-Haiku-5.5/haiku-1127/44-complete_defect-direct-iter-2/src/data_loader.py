"""Loading of the Beijing Subway dataset from subway_data.json."""

import json
import os

_THIS_DIR = os.path.dirname(os.path.abspath(__file__))

# Absolute path of src/subway_data.json, valid from any working directory.
DATA_FILE_PATH = os.path.join(_THIS_DIR, "subway_data.json")


def load_subway_data(path=DATA_FILE_PATH):
    """Load and return the subway dataset as a dictionary.

    Args:
        path: path of the JSON file (defaults to DATA_FILE_PATH).

    Returns:
        dict with the keys "stations" and "connections".

    Raises:
        OSError: if the file cannot be read.
        ValueError: if the JSON is malformed or has an unexpected top-level type.
    """
    with open(path, "r", encoding="utf-8") as fh:
        data = json.load(fh)
    if not isinstance(data, dict):
        raise ValueError("subway data must be a JSON object")
    data.setdefault("stations", [])
    data.setdefault("connections", [])
    if not isinstance(data["stations"], list) or not isinstance(data["connections"], list):
        raise ValueError("'stations' and 'connections' must be JSON arrays")
    return data
