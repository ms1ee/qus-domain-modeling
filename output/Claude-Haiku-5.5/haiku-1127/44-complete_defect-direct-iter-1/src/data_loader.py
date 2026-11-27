"""Data loading utilities for the Beijing Subway dataset.

The dataset lives in ``subway_data.json`` next to this module. The path is
resolved relative to this file so the program works from any working directory.
"""

import json
import os

# Absolute path of src/subway_data.json, valid regardless of the current working directory.
DATA_FILE_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "subway_data.json")


def load_subway_data(path=DATA_FILE_PATH) -> dict:
    """Load the subway dataset from a JSON file.

    Args:
        path: Path of the JSON file. Defaults to DATA_FILE_PATH.

    Returns:
        The parsed JSON content as a dict containing the "stations" and
        "connections" lists.

    Raises:
        FileNotFoundError: If the file does not exist.
        ValueError: If the file is not valid JSON or has an unexpected structure.
    """
    with open(path, "r", encoding="utf-8") as handle:
        try:
            data = json.load(handle)
        except json.JSONDecodeError as exc:
            raise ValueError(f"Invalid JSON in subway data file '{path}': {exc}") from exc

    if not isinstance(data, dict):
        raise ValueError("Subway data must be a JSON object")
    for key in ("stations", "connections"):
        if not isinstance(data.get(key), list):
            raise ValueError(f"Subway data must contain a list under '{key}'")
    return data


def save_subway_data(data, path=DATA_FILE_PATH) -> None:
    """Persist the subway dataset to a JSON file.

    Args:
        data: Dataset dict with "stations" and "connections" lists.
        path: Destination file path. Defaults to DATA_FILE_PATH.
    """
    with open(path, "w", encoding="utf-8") as handle:
        json.dump(data, handle, ensure_ascii=False, indent=2)
        handle.write("\n")
