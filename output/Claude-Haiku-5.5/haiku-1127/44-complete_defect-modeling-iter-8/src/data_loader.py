"""Loading and saving of the Beijing Subway raw dataset (subway_data.json)."""

import json
import os

# Absolute path of subway_data.json, valid regardless of the current working directory.
DATA_FILE_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "subway_data.json")


def load_subway_data(path=DATA_FILE_PATH):
    """Load the subway dataset.

    Args:
        path: Path of the JSON data file.

    Returns:
        dict with keys "stations" and "connections".

    Raises:
        OSError: If the file cannot be read.
        ValueError: If the JSON content is malformed or missing required keys.
    """
    with open(path, "r", encoding="utf-8") as handle:
        try:
            data = json.load(handle)
        except json.JSONDecodeError as exc:
            raise ValueError(f"Invalid JSON in subway data file '{path}': {exc}") from exc

    if not isinstance(data, dict):
        raise ValueError("Subway data must be a JSON object")
    for key in ("stations", "connections"):
        if key not in data or not isinstance(data[key], list):
            raise ValueError(f"Subway data is missing the list field '{key}'")
    return data


def save_subway_data(data, path=DATA_FILE_PATH):
    """Write the subway dataset back to a JSON file.

    Args:
        data: dict with "stations" and "connections" lists.
        path: Destination file path.

    Raises:
        OSError: If the file cannot be written.
    """
    with open(path, "w", encoding="utf-8") as handle:
        json.dump(data, handle, ensure_ascii=False, indent=2)
        handle.write("\n")
