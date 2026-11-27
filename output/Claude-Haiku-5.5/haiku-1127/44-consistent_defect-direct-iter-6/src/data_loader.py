"""Data loading utilities for the Beijing Subway network dataset.

The dataset lives in ``subway_data.json`` next to this module, so the
resolved path is valid regardless of the current working directory.
"""

import json
import os

DATA_FILE_PATH = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "subway_data.json"
)


class DataLoadError(Exception):
    """Raised when the subway dataset cannot be read or is malformed."""


def load_subway_data(path=DATA_FILE_PATH):
    """Load the subway dataset from a JSON file.

    Args:
        path: Path of the JSON file. Defaults to ``DATA_FILE_PATH``.

    Returns:
        dict: The JSON content, with ``stations`` and ``connections`` lists.

    Raises:
        DataLoadError: If the file is missing, unreadable, not valid JSON,
            or does not contain the expected top-level structure.
    """
    try:
        with open(path, "r", encoding="utf-8") as handle:
            data = json.load(handle)
    except FileNotFoundError as exc:
        raise DataLoadError(f"Subway data file not found: {path}") from exc
    except json.JSONDecodeError as exc:
        raise DataLoadError(f"Subway data file is not valid JSON: {exc}") from exc
    except OSError as exc:
        raise DataLoadError(f"Cannot read subway data file: {exc}") from exc

    if not isinstance(data, dict):
        raise DataLoadError("Subway data must be a JSON object.")
    for key in ("stations", "connections"):
        if not isinstance(data.get(key), list):
            raise DataLoadError(f"Subway data has a missing or invalid '{key}' list.")
    return data
