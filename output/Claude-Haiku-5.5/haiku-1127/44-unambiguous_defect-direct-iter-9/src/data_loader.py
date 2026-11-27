"""Loading of the Beijing Subway dataset stored in ``subway_data.json``.

The data file lives next to this module, so ``DATA_FILE_PATH`` is valid no
matter which working directory the program is launched from.
"""

import json
import os

_THIS_DIR = os.path.dirname(os.path.abspath(__file__))

#: Absolute path of ``src/subway_data.json``.
DATA_FILE_PATH = os.path.join(_THIS_DIR, "subway_data.json")


class DataLoadError(Exception):
    """Raised when the subway dataset cannot be read or is malformed."""


def load_subway_data(path=DATA_FILE_PATH):
    """Load the subway dataset from a JSON file.

    Args:
        path: Path of the JSON file. Defaults to ``DATA_FILE_PATH``.

    Returns:
        dict: The JSON content, with ``"stations"`` and ``"connections"`` keys.

    Raises:
        DataLoadError: If the file is missing, is not valid JSON, or does not
            contain the expected top-level structure.
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
            raise DataLoadError(f"subway data is missing the '{key}' list")
    return data
