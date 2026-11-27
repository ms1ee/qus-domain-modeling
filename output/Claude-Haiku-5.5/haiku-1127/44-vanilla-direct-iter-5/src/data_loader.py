"""Loading of the Beijing Subway dataset from ``subway_data.json``.

The data file is located relative to this module, so the loader works
regardless of the current working directory.
"""
from __future__ import annotations

import json
import os

_THIS_DIR = os.path.dirname(os.path.abspath(__file__))

# Absolute path of src/subway_data.json, valid from any working directory.
DATA_FILE_PATH = os.path.join(_THIS_DIR, "subway_data.json")


def load_subway_data(path: str) -> dict:
    """Read and parse the subway dataset file.

    Args:
        path: path of the JSON file to load.

    Returns:
        The parsed JSON content as a dictionary with the keys
        ``stations`` and ``connections``.

    Raises:
        OSError: if the file cannot be opened or read.
        ValueError: if the content is not valid JSON or not a JSON object.
    """
    with open(path, "r", encoding="utf-8") as fh:
        try:
            data = json.load(fh)
        except json.JSONDecodeError as exc:
            raise ValueError(f"Invalid JSON in subway data file '{path}': {exc}") from exc
    if not isinstance(data, dict):
        raise ValueError(f"Subway data file '{path}' must contain a JSON object")
    return data
