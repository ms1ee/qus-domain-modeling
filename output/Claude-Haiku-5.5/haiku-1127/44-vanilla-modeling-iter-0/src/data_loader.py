"""
Data loading utilities for the Beijing Subway network.

The network dataset lives in ``subway_data.json`` next to this module. The
path is resolved relative to this file, so the program works from any
working directory.
"""
from __future__ import annotations

import json
import os

# Absolute path of src/subway_data.json, independent of the current working directory.
DATA_FILE_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "subway_data.json")


def load_subway_data(path: str) -> dict:
    """Load the subway dataset JSON file and return its content as a dictionary.

    Args:
        path: Path of the JSON file to read.

    Returns:
        The parsed JSON content, containing the keys ``stations`` and ``connections``.

    Raises:
        OSError: If the file cannot be opened or read.
        ValueError: If the file is not valid JSON or does not have the expected structure.
    """
    with open(path, "r", encoding="utf-8") as handle:
        try:
            data = json.load(handle)
        except json.JSONDecodeError as exc:
            raise ValueError(f"Invalid JSON in subway data file '{path}': {exc}") from exc

    if not isinstance(data, dict):
        raise ValueError("Subway data must be a JSON object")
    if "stations" not in data or "connections" not in data:
        raise ValueError("Subway data must contain 'stations' and 'connections' keys")
    if not isinstance(data["stations"], list) or not isinstance(data["connections"], list):
        raise ValueError("'stations' and 'connections' must be lists")
    return data
