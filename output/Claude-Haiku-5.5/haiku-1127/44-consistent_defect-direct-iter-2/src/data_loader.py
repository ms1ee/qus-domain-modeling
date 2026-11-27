"""Loading of the Beijing Subway network dataset from its JSON file."""

import json
import os

# Absolute path of src/subway_data.json, valid regardless of the working directory.
DATA_FILE_PATH = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "subway_data.json"
)


class DataLoadError(Exception):
    """Raised when the subway dataset cannot be read or has an invalid structure."""


def load_subway_data(path):
    """Load the subway dataset and return its JSON content as a dict.

    The expected structure is:
        {"stations": [{"name": str, "lines": [str]}],
         "connections": [{"source": str, "dest": str, "distance": int, "line": str}]}

    Raises:
        DataLoadError: if the file is missing, unreadable, not valid JSON,
            or does not contain the expected top-level lists.
    """
    try:
        with open(path, "r", encoding="utf-8") as handle:
            data = json.load(handle)
    except FileNotFoundError as exc:
        raise DataLoadError(f"subway data file not found: {path}") from exc
    except json.JSONDecodeError as exc:
        raise DataLoadError(f"subway data file is not valid JSON: {exc}") from exc
    except OSError as exc:
        raise DataLoadError(f"cannot read subway data file: {exc}") from exc

    if not isinstance(data, dict):
        raise DataLoadError("subway data must be a JSON object")
    for key in ("stations", "connections"):
        if not isinstance(data.get(key), list):
            raise DataLoadError(f"subway data is missing the list field '{key}'")
    return data
