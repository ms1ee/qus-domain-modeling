"""Loading of the Beijing Subway network dataset.

The dataset is stored in ``subway_data.json`` located next to this module,
so it can be found regardless of the current working directory.
"""

import json
import os

DATA_FILE_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "subway_data.json")


class DataLoadError(Exception):
    """Raised when the subway data file cannot be read or is malformed."""


def load_subway_data(path=DATA_FILE_PATH):
    """Load the subway network JSON file.

    Args:
        path: Path of the JSON file. Defaults to ``DATA_FILE_PATH``.

    Returns:
        dict: The JSON content, with keys ``stations`` and ``connections``.

    Raises:
        DataLoadError: If the file is missing, is not valid JSON, or lacks
            the required top-level keys.
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
        if key not in data or not isinstance(data[key], list):
            raise DataLoadError(f"subway data is missing the list '{key}'")
    return data
