"""
Data loading utilities for the Beijing Subway dataset.

The dataset is stored in ``subway_data.json`` located next to this module.
The file has the following structure::

    {"stations": [{"name": str, "lines": [str]}],
     "connections": [{"source": str, "dest": str, "distance": int, "line": str}]}
"""

import json
import os

# Absolute path of src/subway_data.json, valid regardless of the working directory.
DATA_FILE_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "subway_data.json")


class SubwayDataError(Exception):
    """Raised when the subway dataset is missing, unreadable or malformed."""


def load_subway_data(path=DATA_FILE_PATH):
    """
    Load the subway dataset from a JSON file.

    Args:
        path: Path of the JSON file. Defaults to ``DATA_FILE_PATH``.

    Returns:
        dict: The JSON content of the file.

    Raises:
        SubwayDataError: If the file is missing, is not valid JSON, or does not
            contain the required ``stations`` and ``connections`` lists.
    """
    if path is None:
        path = DATA_FILE_PATH

    try:
        with open(path, "r", encoding="utf-8") as handle:
            data = json.load(handle)
    except FileNotFoundError as exc:
        raise SubwayDataError(f"Subway data file not found: {path}") from exc
    except json.JSONDecodeError as exc:
        raise SubwayDataError(f"Subway data file is not valid JSON: {exc}") from exc
    except OSError as exc:
        raise SubwayDataError(f"Cannot read subway data file: {exc}") from exc

    if not isinstance(data, dict):
        raise SubwayDataError("Subway data root must be a JSON object")
    for key in ("stations", "connections"):
        if key not in data or not isinstance(data[key], list):
            raise SubwayDataError(f"Subway data is missing the list '{key}'")
    return data
