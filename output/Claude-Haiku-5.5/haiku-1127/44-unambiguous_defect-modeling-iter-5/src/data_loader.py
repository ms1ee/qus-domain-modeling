"""Loading of the Beijing Subway network dataset (subway_data.json).

The data file is located relative to this module, so the loader works from
any current working directory.
"""

import json
import os

DATA_FILE_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "subway_data.json")


class DataLoadError(Exception):
    """Raised when the subway dataset cannot be read or has an invalid top-level structure."""


def load_subway_data(path=DATA_FILE_PATH):
    """Read the subway dataset file and return its JSON content as a dict.

    Args:
        path: Path to the JSON file. Defaults to DATA_FILE_PATH.

    Returns:
        dict with the keys "stations" and "connections".

    Raises:
        DataLoadError: If the file is missing, unreadable, not valid JSON,
            or lacks the required top-level structure.
    """
    if path is None:
        path = DATA_FILE_PATH
    try:
        with open(path, "r", encoding="utf-8") as fh:
            data = json.load(fh)
    except FileNotFoundError as exc:
        raise DataLoadError(f"Data file not found: {path}") from exc
    except json.JSONDecodeError as exc:
        raise DataLoadError(f"Data file is not valid JSON ({path}): {exc}") from exc
    except OSError as exc:
        raise DataLoadError(f"Cannot read data file ({path}): {exc}") from exc

    if not isinstance(data, dict):
        raise DataLoadError("Data file must contain a JSON object at the top level")
    for key in ("stations", "connections"):
        if not isinstance(data.get(key), list):
            raise DataLoadError(f"Data file must contain a list under the key '{key}'")
    return data
