"""Loading and saving of the Beijing Subway raw dataset (subway_data.json)."""

import json
import os

# Absolute path of src/subway_data.json, valid from any working directory.
DATA_FILE_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "subway_data.json")


def load_subway_data(path=DATA_FILE_PATH):
    """Load the subway dataset and return its JSON content as a dict.

    Raises:
        OSError: if the file cannot be read.
        ValueError: if the JSON content does not have the expected structure.
    """
    with open(path, "r", encoding="utf-8") as fh:
        data = json.load(fh)
    if (not isinstance(data, dict)
            or not isinstance(data.get("stations"), list)
            or not isinstance(data.get("connections"), list)):
        raise ValueError("subway data must contain 'stations' and 'connections' lists")
    return data


def save_subway_data(data, path=DATA_FILE_PATH):
    """Write the subway dataset back to a JSON file."""
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(data, fh, ensure_ascii=False, indent=2)
