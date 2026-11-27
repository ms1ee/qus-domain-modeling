"""Loading of the Beijing Subway dataset stored in ``subway_data.json``.

The dataset has the following shape::

    {"stations": [{"name": str, "lines": [str]}],
     "connections": [{"source": str, "dest": str, "distance": int, "line": str}]}

``distance`` is expressed in meters.
"""

import json
import os

# Absolute path of the bundled dataset, valid regardless of the working directory.
DATA_FILE_PATH = os.path.normpath(
    os.path.join(os.path.dirname(os.path.abspath(__file__)), "subway_data.json")
)


class DataLoadError(Exception):
    """Raised when the subway dataset cannot be read or has an invalid structure."""


def load_subway_data(path):
    """Load the subway dataset from a JSON file.

    Args:
        path: Path of the JSON file to read.

    Returns:
        dict: The JSON content of the file with ``stations`` and ``connections`` keys.

    Raises:
        DataLoadError: If the file is missing, is not valid JSON or has an invalid structure.
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

    if (
        not isinstance(data, dict)
        or not isinstance(data.get("stations"), list)
        or not isinstance(data.get("connections"), list)
    ):
        raise DataLoadError(
            "Subway data must be an object with 'stations' and 'connections' lists"
        )
    return data
