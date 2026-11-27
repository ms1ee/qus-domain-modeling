"""Loading and saving of the Beijing Subway network data file.

The data file is ``subway_data.json`` located in the same directory as this
module, so the default path works from any working directory.
"""

import json
import os
from typing import Any, Dict

_SRC_DIR = os.path.dirname(os.path.abspath(__file__))

# Absolute path of src/subway_data.json (valid from any working directory).
DATA_FILE_PATH = os.path.join(_SRC_DIR, "subway_data.json")


def load_subway_data(path: str = DATA_FILE_PATH) -> Dict[str, Any]:
    """Load the subway dataset from a JSON file.

    Args:
        path: Path of the JSON file.

    Returns:
        The JSON content as a dictionary with the keys ``stations`` and
        ``connections``.

    Raises:
        OSError: If the file cannot be read.
        ValueError: If the JSON is malformed or lacks required sections.
    """
    with open(path, "r", encoding="utf-8") as handle:
        data = json.load(handle)
    if not isinstance(data, dict):
        raise ValueError("subway data must be a JSON object")
    for key in ("stations", "connections"):
        if not isinstance(data.get(key), list):
            raise ValueError(f"subway data is missing the '{key}' list")
    return data


def save_subway_data(data: Dict[str, Any], path: str = DATA_FILE_PATH) -> None:
    """Write the subway dataset back to a JSON file.

    Args:
        data: Dataset dictionary in the same layout as the data file.
        path: Destination file path.

    Raises:
        OSError: If the file cannot be written.
    """
    with open(path, "w", encoding="utf-8") as handle:
        json.dump(data, handle, ensure_ascii=False, indent=2)
        handle.write("\n")
