"""
Data loading utilities for the Beijing Subway fare calculation system.

The subway network data is stored in ``subway_data.json`` located next to
this module.  ``DATA_FILE_PATH`` is an absolute path, so it is valid no
matter what the current working directory is.

Expected JSON layout::

    {
        "stations":    [{"name": str, "lines": [str, ...]}, ...],
        "connections": [{"source": str, "dest": str,
                         "distance": int (meters), "line": str}, ...]
    }
"""

import json
import os

# Absolute path of src/subway_data.json (independent of the working directory)
DATA_FILE_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "subway_data.json")


def load_subway_data(path=DATA_FILE_PATH):
    """Load and return the JSON content of the subway data file.

    :param path: path of the JSON data file (defaults to ``DATA_FILE_PATH``)
    :return: the parsed JSON content (a dict)
    :raises FileNotFoundError: if the file does not exist
    :raises ValueError: if the file is not valid JSON or has a wrong structure
    """
    if path is None:
        path = DATA_FILE_PATH
    if not os.path.isfile(path):
        raise FileNotFoundError(f"Subway data file not found: {path}")
    try:
        with open(path, "r", encoding="utf-8") as fh:
            data = json.load(fh)
    except json.JSONDecodeError as exc:
        raise ValueError(f"Subway data file '{path}' is not valid JSON: {exc}") from exc

    if not isinstance(data, dict):
        raise ValueError("Subway data must be a JSON object")
    # Be tolerant: missing sections default to empty lists.
    data.setdefault("stations", [])
    data.setdefault("connections", [])
    if not isinstance(data["stations"], list) or not isinstance(data["connections"], list):
        raise ValueError("'stations' and 'connections' must be JSON arrays")
    return data


def save_subway_data(data, path=DATA_FILE_PATH):
    """Write subway data (same layout as the input file) back to disk."""
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(data, fh, ensure_ascii=False, indent=2)
