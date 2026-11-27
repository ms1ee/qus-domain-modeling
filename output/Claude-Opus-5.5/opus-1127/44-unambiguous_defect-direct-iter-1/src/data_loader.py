"""Data loading utilities for the Beijing Subway fare calculation system.

The subway network data is stored in ``subway_data.json`` located next to
this module.  ``DATA_FILE_PATH`` is an absolute path so that it is valid no
matter what the current working directory is.
"""

import json
import os

DATA_FILE_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "subway_data.json")


class DataLoadError(Exception):
    """Raised when the subway data file cannot be loaded."""


def load_subway_data(path=DATA_FILE_PATH):
    """Load the subway network JSON file and return its content as a dict.

    :param path: path of the JSON data file (defaults to ``DATA_FILE_PATH``)
    :return: dict with keys ``stations`` and ``connections``
    :raises DataLoadError: when the file is missing or malformed
    """
    if path is None:
        path = DATA_FILE_PATH
    try:
        with open(path, "r", encoding="utf-8") as fh:
            data = json.load(fh)
    except FileNotFoundError as exc:
        raise DataLoadError(f"Data file not found: {path}") from exc
    except json.JSONDecodeError as exc:
        raise DataLoadError(f"Data file is not valid JSON: {path} ({exc})") from exc
    except OSError as exc:
        raise DataLoadError(f"Cannot read data file: {path} ({exc})") from exc

    if not isinstance(data, dict):
        raise DataLoadError("Data file root must be a JSON object")
    data.setdefault("stations", [])
    data.setdefault("connections", [])
    return data


def save_subway_data(data, path=DATA_FILE_PATH):
    """Write subway network data back to a JSON file."""
    if path is None:
        path = DATA_FILE_PATH
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(data, fh, ensure_ascii=False, indent=2)
