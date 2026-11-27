"""
Data loading utilities for the Beijing Subway fare calculation system.

The subway dataset is stored in ``subway_data.json`` located in the same
directory as this module, so the path is valid regardless of the current
working directory.
"""

import json
import os

# Absolute path of the dataset file (src/subway_data.json).
DATA_FILE_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "subway_data.json")


def load_subway_data(path=DATA_FILE_PATH):
    """
    Load the subway dataset from a JSON file.

    Args:
        path: Path of the JSON file. Defaults to ``DATA_FILE_PATH``.

    Returns:
        dict: The JSON content, expected to contain the keys
              ``"stations"`` (list of {"name", "lines"}) and
              ``"connections"`` (list of {"source", "dest", "distance", "line"}).

    Raises:
        OSError: If the file cannot be opened.
        ValueError: If the file content is not valid JSON or not a JSON object.
    """
    with open(path, "r", encoding="utf-8") as fh:
        data = json.load(fh)
    if not isinstance(data, dict):
        raise ValueError("Subway data file must contain a JSON object at the top level")
    return data
