"""Loading of the Beijing Subway dataset from the bundled JSON file.

The dataset lives in ``subway_data.json`` next to this module, so the
default path is valid no matter which directory the program is started from.
"""

import json
import os

from errors import DataError

# Absolute path of src/subway_data.json, independent of the working directory.
DATA_FILE_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "subway_data.json")


def load_subway_data(path=DATA_FILE_PATH):
    """Read the subway dataset and return its JSON content as a dictionary.

    Args:
        path: Path of the JSON file. Defaults to DATA_FILE_PATH.

    Returns:
        dict: The parsed JSON object with the keys "stations" and "connections".

    Raises:
        DataError: If the file is missing, unreadable, not valid JSON, or the
            root element is not a JSON object.
    """
    file_path = os.path.abspath(os.fspath(path))
    try:
        with open(file_path, "r", encoding="utf-8") as fh:
            data = json.load(fh)
    except FileNotFoundError as exc:
        raise DataError(f"subway data file not found: {file_path}") from exc
    except json.JSONDecodeError as exc:
        raise DataError(f"subway data file is not valid JSON: {exc}") from exc
    except OSError as exc:
        raise DataError(f"cannot read subway data file: {exc}") from exc

    if not isinstance(data, dict):
        raise DataError("subway data root must be a JSON object")
    return data
