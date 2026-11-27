"""Loading of the Beijing Subway network dataset (subway_data.json).

The data file lives next to this module, so the path is valid from any
working directory.
"""

import json
import os

# Absolute path of src/subway_data.json, independent of the current working directory.
DATA_FILE_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "subway_data.json")


def load_subway_data(path=DATA_FILE_PATH) -> dict:
    """Load and return the JSON content of the subway dataset.

    Args:
        path: Path to the JSON file. Defaults to DATA_FILE_PATH.

    Returns:
        A dict with keys "stations" and "connections".

    Raises:
        OSError: If the file cannot be read.
        ValueError: If the JSON content is malformed or not an object.
    """
    with open(path, "r", encoding="utf-8") as handle:
        try:
            data = json.load(handle)
        except json.JSONDecodeError as exc:
            raise ValueError(f"Invalid JSON in subway data file {path}: {exc}") from exc
    if not isinstance(data, dict):
        raise ValueError("Subway data root must be a JSON object")
    data.setdefault("stations", [])
    data.setdefault("connections", [])
    return data
