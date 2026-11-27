"""
Data loading utilities for the Beijing Subway network.

Provides the location of the bundled ``subway_data.json`` file and functions
to read and persist the raw network data dictionary.
"""

import json
import os

# Absolute path of src/subway_data.json, valid regardless of the working directory.
DATA_FILE_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "subway_data.json")


def load_subway_data(path):
    """
    Load the subway network data from a JSON file.

    Args:
        path: Path to the JSON file.

    Returns:
        dict: The JSON content, with the keys "stations" and "connections".

    Raises:
        FileNotFoundError: If the file does not exist.
        ValueError: If the file is not valid JSON or does not have the expected structure.
    """
    with open(path, "r", encoding="utf-8") as handle:
        data = json.load(handle)

    if not isinstance(data, dict):
        raise ValueError("Subway data must be a JSON object")
    for key in ("stations", "connections"):
        if key not in data or not isinstance(data[key], list):
            raise ValueError(f"Subway data is missing the list field '{key}'")
    return data


def save_subway_data(data, path):
    """
    Write the subway network data dictionary to a JSON file.

    Args:
        data: The network data dictionary.
        path: Destination file path.

    Raises:
        OSError: If the file cannot be written.
    """
    with open(path, "w", encoding="utf-8") as handle:
        json.dump(data, handle, ensure_ascii=False, indent=2)
        handle.write("\n")
