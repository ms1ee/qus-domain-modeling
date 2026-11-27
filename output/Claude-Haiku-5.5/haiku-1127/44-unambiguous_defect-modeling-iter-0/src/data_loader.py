"""
Data loading utilities for the Beijing Subway fare calculation system.

The subway network dataset is stored in ``subway_data.json`` located in the
same directory as this module, so it can be found regardless of the current
working directory.
"""

import json
import os

# Absolute path of the subway dataset, valid from any working directory.
DATA_FILE_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "subway_data.json")


def load_subway_data(path):
    """
    Load the subway network dataset from a JSON file.

    Args:
        path: Path to the JSON file.

    Returns:
        dict: The JSON content, expected to contain "stations" and "connections".

    Raises:
        OSError: If the file cannot be read.
        ValueError: If the file is not valid JSON or does not contain a JSON object.
    """
    with open(path, "r", encoding="utf-8") as fh:
        data = json.load(fh)
    if not isinstance(data, dict):
        raise ValueError("Subway data file must contain a JSON object at the top level")
    return data


def save_subway_data(data, path):
    """
    Persist the subway network dataset to a JSON file.

    Args:
        data: Dictionary with "stations" and "connections" keys.
        path: Destination file path.

    Raises:
        OSError: If the file cannot be written.
    """
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(data, fh, ensure_ascii=False, indent=2)
        fh.write("\n")
