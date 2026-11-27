"""Data loading utilities for the Beijing Subway network.

The network dataset lives in ``subway_data.json`` next to this module. The
path is resolved relative to this file so the program works from any
working directory.
"""

import json
import os

DATA_FILE_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "subway_data.json")


def load_subway_data(path=DATA_FILE_PATH) -> dict:
    """Load the subway network JSON file and return its content as a dict.

    Args:
        path: Path to the JSON data file.

    Returns:
        The parsed JSON content (a dict with "stations" and "connections").

    Raises:
        OSError: If the file cannot be read.
        ValueError: If the content is not valid JSON or not a JSON object.
    """
    with open(path, "r", encoding="utf-8") as handle:
        data = json.load(handle)
    if not isinstance(data, dict):
        raise ValueError("Subway data file must contain a JSON object at the top level")
    return data
