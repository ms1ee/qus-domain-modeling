"""Loading and saving of the Beijing Subway dataset stored in ``subway_data.json``.

The JSON file has the following shape::

    {"stations": [{"name": str, "lines": [str]}],
     "connections": [{"source": str, "dest": str, "distance": int, "line": str}]}

``distance`` is expressed in meters.
"""

import json
import os

# Absolute path of the bundled dataset, valid regardless of the working directory.
DATA_FILE_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "subway_data.json")


class DataLoadError(Exception):
    """Raised when the subway dataset cannot be read or has an invalid structure."""


def load_subway_data(path=DATA_FILE_PATH):
    """Read the subway dataset file and return its JSON content as a dictionary.

    Args:
        path: Path of the JSON file. Defaults to ``DATA_FILE_PATH``.

    Returns:
        dict: The parsed JSON content.

    Raises:
        DataLoadError: If the file is missing, is not valid JSON, or does not
            contain the expected top-level structure.
    """
    if path is None:
        path = DATA_FILE_PATH
    try:
        with open(path, "r", encoding="utf-8") as handle:
            data = json.load(handle)
    except FileNotFoundError as exc:
        raise DataLoadError(f"Subway data file not found: {path}") from exc
    except json.JSONDecodeError as exc:
        raise DataLoadError(f"Subway data file is not valid JSON: {exc}") from exc
    except OSError as exc:
        raise DataLoadError(f"Cannot read subway data file '{path}': {exc}") from exc

    if not isinstance(data, dict):
        raise DataLoadError("Subway data must be a JSON object")
    if not isinstance(data.get("stations", []), list):
        raise DataLoadError("'stations' must be a list")
    if not isinstance(data.get("connections", []), list):
        raise DataLoadError("'connections' must be a list")
    return data


def save_subway_data(data, path=DATA_FILE_PATH):
    """Write a dataset dictionary back to a JSON file.

    Args:
        data: Dictionary with ``stations`` and ``connections`` keys.
        path: Destination file path.

    Raises:
        DataLoadError: If the file cannot be written.
    """
    try:
        with open(path, "w", encoding="utf-8") as handle:
            json.dump(data, handle, ensure_ascii=False, indent=2)
            handle.write("\n")
    except OSError as exc:
        raise DataLoadError(f"Cannot write subway data file '{path}': {exc}") from exc
