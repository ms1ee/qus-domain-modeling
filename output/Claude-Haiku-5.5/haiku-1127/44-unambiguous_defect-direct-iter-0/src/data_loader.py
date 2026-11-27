"""Data loading utilities for the Beijing Subway network dataset.

The dataset lives in ``subway_data.json`` next to this module, so the
location is resolved relative to this file and works from any working
directory.
"""

import json
import os


_THIS_DIR = os.path.dirname(os.path.abspath(__file__))

# Absolute path of src/subway_data.json, valid from any working directory.
DATA_FILE_PATH = os.path.join(_THIS_DIR, "subway_data.json")


class DataLoadError(Exception):
    """Raised when the subway dataset cannot be read or parsed."""


def load_subway_data(path=DATA_FILE_PATH):
    """Load and return the JSON content of the subway dataset file.

    The returned dictionary has the structure::

        {"stations": [{"name": str, "lines": [str]}],
         "connections": [{"source": str, "dest": str,
                          "distance": int, "line": str}]}

    Missing top-level keys are replaced by empty lists.
    """
    try:
        with open(path, "r", encoding="utf-8") as fh:
            data = json.load(fh)
    except FileNotFoundError as exc:
        raise DataLoadError(f"data file not found: {path}") from exc
    except json.JSONDecodeError as exc:
        raise DataLoadError(f"data file is not valid JSON: {exc}") from exc
    except OSError as exc:
        raise DataLoadError(f"cannot read data file: {exc}") from exc

    if not isinstance(data, dict):
        raise DataLoadError("data file must contain a JSON object")
    data.setdefault("stations", [])
    data.setdefault("connections", [])
    return data
