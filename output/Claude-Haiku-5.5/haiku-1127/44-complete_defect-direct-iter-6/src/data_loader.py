"""Loading and saving of the Beijing Subway network data file.

The data file is located at src/subway_data.json and has the structure:
    {"stations": [{"name": str, "lines": [str]}],
     "connections": [{"source": str, "dest": str, "distance": int, "line": str}]}
"""

import json
import os
from typing import Any, Dict

DATA_FILE_PATH = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "subway_data.json"
)


def load_subway_data(path: str = DATA_FILE_PATH) -> Dict[str, Any]:
    """Load the subway dataset from a JSON file.

    Args:
        path: path of the JSON file (defaults to DATA_FILE_PATH).

    Returns:
        The decoded JSON content as a dictionary.

    Raises:
        OSError: if the file cannot be read.
        ValueError: if the content is not valid JSON or lacks the expected keys.
    """
    with open(path, "r", encoding="utf-8") as handle:
        try:
            data = json.load(handle)
        except json.JSONDecodeError as exc:
            raise ValueError(f"invalid JSON in {path}: {exc}") from exc

    if not isinstance(data, dict):
        raise ValueError("subway data root must be a JSON object")
    if not isinstance(data.get("stations"), list):
        raise ValueError("subway data must contain a 'stations' list")
    if not isinstance(data.get("connections"), list):
        raise ValueError("subway data must contain a 'connections' list")
    return data


def save_subway_data(data: Dict[str, Any], path: str = DATA_FILE_PATH) -> None:
    """Write the subway dataset back to a JSON file (UTF-8, pretty-printed)."""
    with open(path, "w", encoding="utf-8") as handle:
        json.dump(data, handle, ensure_ascii=False, indent=2)
        handle.write("\n")
