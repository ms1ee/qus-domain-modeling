"""Loading of the raw Beijing Subway dataset from ``subway_data.json``.

The dataset file lives next to this module, so the path is valid no matter
which working directory the program is started from.
"""

import json
import os

from errors import DataError

DATA_FILE_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "subway_data.json")


def load_subway_data(path: str = DATA_FILE_PATH) -> dict:
    """Read the subway dataset JSON file and return its content as a dict.

    Args:
        path: Location of the JSON file. Defaults to ``DATA_FILE_PATH``.

    Returns:
        The parsed JSON object (expected keys: ``stations`` and ``connections``).

    Raises:
        DataError: If the file is missing, is not valid JSON, or is not an object.
    """
    try:
        with open(path, "r", encoding="utf-8") as handle:
            data = json.load(handle)
    except FileNotFoundError as exc:
        raise DataError(f"subway data file not found: {path}") from exc
    except json.JSONDecodeError as exc:
        raise DataError(f"subway data file is not valid JSON: {exc}") from exc
    except OSError as exc:
        raise DataError(f"cannot read subway data file: {exc}") from exc

    if not isinstance(data, dict):
        raise DataError("subway data file must contain a JSON object")
    return data
