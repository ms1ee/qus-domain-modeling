"""Loading of the Beijing Subway network data file.

The data file ``subway_data.json`` lives next to this module, so its path is
resolved relative to this file.  It is therefore valid regardless of the
current working directory.

File layout::

    {"stations": [{"name": str, "lines": [str]}],
     "connections": [{"source": str, "dest": str,
                      "distance": int (meters), "line": str}]}
"""

import json
import os

# Absolute path of src/subway_data.json, valid from any working directory.
DATA_FILE_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "subway_data.json")


class DataLoadError(Exception):
    """Raised when the subway data file cannot be loaded or parsed."""


def load_subway_data(path=DATA_FILE_PATH):
    """Load the subway data file and return its JSON content as a dict.

    :param path: path of the JSON file (defaults to ``DATA_FILE_PATH``).
    :raises DataLoadError: when the file is missing, unreadable or malformed.
    """
    if path is None:
        path = DATA_FILE_PATH
    try:
        with open(path, "r", encoding="utf-8") as handle:
            data = json.load(handle)
    except FileNotFoundError as exc:
        raise DataLoadError(f"Subway data file not found: {path}") from exc
    except json.JSONDecodeError as exc:
        raise DataLoadError(f"Subway data file is not valid JSON: {path} ({exc})") from exc
    except OSError as exc:
        raise DataLoadError(f"Unable to read subway data file: {path} ({exc})") from exc

    if not isinstance(data, dict):
        raise DataLoadError("Subway data file must contain a JSON object at the top level")
    data.setdefault("stations", [])
    data.setdefault("connections", [])
    return data
