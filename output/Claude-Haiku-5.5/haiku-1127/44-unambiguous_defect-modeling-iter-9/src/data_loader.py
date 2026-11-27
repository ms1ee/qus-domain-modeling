"""Loading and saving of the raw Beijing Subway dataset (subway_data.json)."""

import json
import os

# Absolute path of the dataset file, valid regardless of the working directory.
DATA_FILE_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "subway_data.json")


class DataLoadError(Exception):
    """Raised when the subway dataset cannot be read or has an invalid structure."""


def load_subway_data(path=DATA_FILE_PATH):
    """Load the subway dataset from a JSON file and return its content as a dict.

    Args:
        path: path of the JSON file.

    Returns:
        dict with keys "stations" and "connections".

    Raises:
        DataLoadError: if the file is missing, not valid JSON, or malformed.
    """
    try:
        with open(path, "r", encoding="utf-8") as fh:
            data = json.load(fh)
    except FileNotFoundError as exc:
        raise DataLoadError(f"Subway data file not found: {path}") from exc
    except json.JSONDecodeError as exc:
        raise DataLoadError(f"Subway data file is not valid JSON: {path} ({exc})") from exc
    except OSError as exc:
        raise DataLoadError(f"Cannot read subway data file: {path} ({exc})") from exc

    if not isinstance(data, dict):
        raise DataLoadError("Subway data must be a JSON object")
    if not isinstance(data.get("stations"), list) or not isinstance(data.get("connections"), list):
        raise DataLoadError("Subway data must contain 'stations' and 'connections' lists")
    return data


def save_subway_data(data, path=DATA_FILE_PATH):
    """Write the dataset dict back to a JSON file.

    Raises:
        DataLoadError: if the file cannot be written.
    """
    try:
        with open(path, "w", encoding="utf-8") as fh:
            json.dump(data, fh, ensure_ascii=False, indent=2)
            fh.write("\n")
    except OSError as exc:
        raise DataLoadError(f"Cannot write subway data file: {path} ({exc})") from exc
