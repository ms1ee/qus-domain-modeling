"""Loading of the Beijing Subway network data file (subway_data.json)."""
import json
import os

# Absolute path of the data file, valid from any working directory.
DATA_FILE_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "subway_data.json")


def load_subway_data(path=DATA_FILE_PATH) -> dict:
    """Load and return the JSON content of the subway data file."""
    if path is None:
        path = DATA_FILE_PATH
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    if not isinstance(data, dict):
        raise ValueError("Subway data file must contain a JSON object")
    data.setdefault("stations", [])
    data.setdefault("connections", [])
    return data
