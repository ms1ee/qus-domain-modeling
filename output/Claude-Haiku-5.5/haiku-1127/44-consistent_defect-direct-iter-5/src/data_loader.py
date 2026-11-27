"""Loading of the Beijing Subway network dataset.

The dataset lives in ``subway_data.json`` next to this module, so it can be
located correctly regardless of the current working directory.
"""

import json
import os

_THIS_DIR = os.path.dirname(os.path.abspath(__file__))

# Absolute path of src/subway_data.json, valid from any working directory.
DATA_FILE_PATH = os.path.join(_THIS_DIR, "subway_data.json")


def load_subway_data(path=DATA_FILE_PATH) -> dict:
    """Load and minimally validate the subway dataset.

    Args:
        path: Path of the JSON file. Defaults to ``DATA_FILE_PATH``.

    Returns:
        The parsed JSON content as a dictionary with the keys
        ``"stations"`` and ``"connections"``.

    Raises:
        OSError: If the file cannot be read.
        ValueError: If the JSON is malformed or lacks the required structure.
    """
    with open(path, "r", encoding="utf-8") as handle:
        data = json.load(handle)

    if not isinstance(data, dict):
        raise ValueError("Subway data must be a JSON object")
    for key in ("stations", "connections"):
        if key not in data or not isinstance(data[key], list):
            raise ValueError(f"Subway data must contain a list named '{key}'")
    return data
