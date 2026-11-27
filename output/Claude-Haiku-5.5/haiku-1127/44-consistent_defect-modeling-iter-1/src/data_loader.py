"""Loading of the Beijing Subway network dataset.

The dataset is stored in ``subway_data.json`` located next to this module.
The file has the structure::

    {"stations": [{"name": str, "lines": [str]}],
     "connections": [{"source": str, "dest": str, "distance": int, "line": str}]}

Connections are directed: each one is usable only in its listed direction,
unless the entry explicitly sets ``"bidirectional": true``.
"""

import json
import os

# Absolute path of the data file; valid regardless of the current working directory.
DATA_FILE_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "subway_data.json")


class DataLoadError(Exception):
    """Raised when the subway dataset cannot be read or is malformed."""


def load_subway_data(path=DATA_FILE_PATH):
    """Read and validate the subway dataset.

    Args:
        path: Path to the JSON file. Defaults to ``DATA_FILE_PATH``.

    Returns:
        dict: The parsed JSON content with ``stations`` and ``connections`` lists.

    Raises:
        DataLoadError: If the file is missing, not valid JSON, or structurally invalid.
    """
    if not path:
        path = DATA_FILE_PATH
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
        raise DataLoadError("Subway data must be a JSON object")
    for key in ("stations", "connections"):
        if key not in data or not isinstance(data[key], list):
            raise DataLoadError(f"Subway data is missing list field '{key}'")

    for index, station in enumerate(data["stations"]):
        if not isinstance(station, dict) or "name" not in station:
            raise DataLoadError(f"Station entry #{index} has no 'name'")
    for index, conn in enumerate(data["connections"]):
        for field in ("source", "dest", "distance", "line"):
            if not isinstance(conn, dict) or field not in conn:
                raise DataLoadError(f"Connection entry #{index} is missing '{field}'")
    return data
