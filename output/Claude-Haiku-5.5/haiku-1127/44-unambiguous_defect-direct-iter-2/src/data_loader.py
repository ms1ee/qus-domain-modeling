"""Loading and saving of the Beijing Subway dataset (subway_data.json)."""

import json
import os

# Absolute path of src/subway_data.json, valid regardless of the working directory.
DATA_FILE_PATH = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "subway_data.json"
)


class DataLoadError(Exception):
    """Raised when the subway dataset cannot be read, parsed or saved."""


def load_subway_data(path=DATA_FILE_PATH):
    """Load the subway dataset from a JSON file.

    Args:
        path: path of the JSON file (defaults to DATA_FILE_PATH).

    Returns:
        dict with the keys 'stations' and 'connections' as stored in the file.

    Raises:
        DataLoadError: if the file is missing, unreadable, not valid JSON, or
            does not have the expected top-level structure.
    """
    if path is None:
        path = DATA_FILE_PATH
    try:
        with open(path, "r", encoding="utf-8") as handle:
            data = json.load(handle)
    except FileNotFoundError as exc:
        raise DataLoadError(f"subway data file not found: {path}") from exc
    except json.JSONDecodeError as exc:
        raise DataLoadError(f"subway data file is not valid JSON: {exc}") from exc
    except OSError as exc:
        raise DataLoadError(f"cannot read subway data file '{path}': {exc}") from exc

    if (
        not isinstance(data, dict)
        or not isinstance(data.get("stations"), list)
        or not isinstance(data.get("connections"), list)
    ):
        raise DataLoadError(
            "subway data must be a JSON object with 'stations' and 'connections' lists"
        )
    return data


def save_subway_data(data, path=DATA_FILE_PATH):
    """Persist the subway dataset to a JSON file.

    The file is written to a temporary sibling first and then atomically
    replaced, so an interrupted write does not corrupt the original data.

    Raises:
        DataLoadError: if the file cannot be written.
    """
    if path is None:
        path = DATA_FILE_PATH
    temp_path = path + ".tmp"
    try:
        with open(temp_path, "w", encoding="utf-8") as handle:
            json.dump(data, handle, ensure_ascii=False, indent=2)
        os.replace(temp_path, path)
    except OSError as exc:
        raise DataLoadError(f"cannot write subway data file '{path}': {exc}") from exc
