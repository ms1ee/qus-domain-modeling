"""Loading and saving of the Beijing Subway network dataset (subway_data.json)."""

import json
import os

# Absolute path of src/subway_data.json, valid from any working directory.
DATA_FILE_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "subway_data.json")


def load_subway_data(path=DATA_FILE_PATH):
    """Load the subway dataset and return its JSON content as a dict.

    Raises:
        OSError: if the file cannot be read.
        ValueError: if the JSON is malformed or lacks the required top-level keys.
    """
    with open(path, "r", encoding="utf-8") as handle:
        data = json.load(handle)

    if not isinstance(data, dict):
        raise ValueError("Subway data must be a JSON object")
    for key in ("stations", "connections"):
        if key not in data or not isinstance(data[key], list):
            raise ValueError(f"Subway data is missing the '{key}' list")
    return data


def save_subway_data(data, path=DATA_FILE_PATH):
    """Write the dataset dict back to a JSON file (UTF-8, pretty-printed)."""
    with open(path, "w", encoding="utf-8") as handle:
        json.dump(data, handle, ensure_ascii=False, indent=2)
        handle.write("\n")
