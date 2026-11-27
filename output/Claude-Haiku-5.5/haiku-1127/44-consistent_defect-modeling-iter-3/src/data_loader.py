"""Loading of the Beijing Subway dataset from the JSON data file."""

import json
import os

# Absolute path of src/subway_data.json, valid regardless of the working directory.
DATA_FILE_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "subway_data.json")


class DataLoadError(Exception):
    """Raised when the subway dataset cannot be read or has an invalid structure."""


def load_subway_data(path=DATA_FILE_PATH) -> dict:
    """Load and minimally validate the subway dataset.

    Args:
        path: Path of the JSON file.

    Returns:
        The parsed JSON content as a dictionary.

    Raises:
        DataLoadError: If the file is missing, not valid JSON, or lacks the
            required 'stations' and 'connections' lists.
    """
    try:
        with open(path, "r", encoding="utf-8") as handle:
            data = json.load(handle)
    except FileNotFoundError as exc:
        raise DataLoadError(f"subway data file not found: {path}") from exc
    except json.JSONDecodeError as exc:
        raise DataLoadError(f"subway data file is not valid JSON: {exc}") from exc

    if not isinstance(data, dict):
        raise DataLoadError("top-level JSON value must be an object")
    for key in ("stations", "connections"):
        if not isinstance(data.get(key), list):
            raise DataLoadError(f"missing or invalid '{key}' list in subway data")
    return data
