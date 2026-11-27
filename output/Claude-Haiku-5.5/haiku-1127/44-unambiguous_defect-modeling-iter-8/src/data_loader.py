"""Loading of the Beijing Subway network dataset.

The dataset is stored in ``subway_data.json`` located next to this module, so
the program works regardless of the current working directory.
"""

import json
import os

DATA_FILE_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "subway_data.json")


class DataLoadError(Exception):
    """Raised when the subway dataset cannot be read or is malformed."""


def load_subway_data(path=None):
    """Load the subway dataset from a JSON file.

    Args:
        path: Path of the JSON file. Defaults to ``DATA_FILE_PATH``.

    Returns:
        dict: The JSON content with at least the keys ``stations`` and
        ``connections``.

    Raises:
        DataLoadError: If the file is missing, not valid JSON, or lacks the
        required top-level keys.
    """
    if path is None:
        path = DATA_FILE_PATH
    try:
        with open(path, "r", encoding="utf-8") as handle:
            data = json.load(handle)
    except FileNotFoundError as exc:
        raise DataLoadError(f"data file not found: {path}") from exc
    except json.JSONDecodeError as exc:
        raise DataLoadError(f"data file is not valid JSON: {path} ({exc})") from exc
    except OSError as exc:
        raise DataLoadError(f"cannot read data file: {path} ({exc})") from exc

    if not isinstance(data, dict):
        raise DataLoadError("data file root must be a JSON object")
    for key in ("stations", "connections"):
        if key not in data or not isinstance(data[key], list):
            raise DataLoadError(f"data file is missing list field '{key}'")
    return data
