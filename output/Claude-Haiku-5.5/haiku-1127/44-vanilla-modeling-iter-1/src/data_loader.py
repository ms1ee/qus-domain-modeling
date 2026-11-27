"""Loading and saving of the raw Beijing Subway dataset (subway_data.json).

The dataset has the form:
    {"stations": [{"name": str, "lines": [str]}],
     "connections": [{"source": str, "dest": str, "distance": int, "line": str}]}
"""

import json
import os

# Absolute path of the bundled dataset; valid regardless of the working directory.
DATA_FILE_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "subway_data.json")


def load_subway_data(path=DATA_FILE_PATH) -> dict:
    """Load and return the JSON content of the subway dataset file.

    Raises:
        OSError: if the file cannot be read.
        ValueError: if the file is not valid JSON or has an unexpected structure.
    """
    try:
        with open(path, "r", encoding="utf-8") as handle:
            data = json.load(handle)
    except json.JSONDecodeError as exc:
        raise ValueError(f"Invalid JSON in '{path}': {exc}") from exc

    if not isinstance(data, dict):
        raise ValueError(f"Dataset '{path}' must contain a JSON object at top level")
    for key in ("stations", "connections"):
        if key in data and not isinstance(data[key], list):
            raise ValueError(f"Dataset key '{key}' must be a list")
    return data


def save_subway_data(data: dict, path=DATA_FILE_PATH) -> None:
    """Write the dataset dictionary back to a JSON file (UTF-8, pretty printed)."""
    with open(path, "w", encoding="utf-8") as handle:
        json.dump(data, handle, ensure_ascii=False, indent=2)
        handle.write("\n")
