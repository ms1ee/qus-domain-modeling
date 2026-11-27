"""Loading of the Beijing Subway network dataset.

The dataset lives in ``subway_data.json`` next to this module, so the path is
valid regardless of the current working directory.
"""

import json
import os

DATA_FILE_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "subway_data.json")


def load_subway_data(path=DATA_FILE_PATH) -> dict:
    """Load the subway dataset from a JSON file.

    Args:
        path: Path of the JSON file. Defaults to ``DATA_FILE_PATH``.

    Returns:
        The parsed JSON content as a dictionary with the keys ``stations``
        and ``connections`` (missing keys are filled with empty lists).

    Raises:
        OSError: If the file cannot be read.
        json.JSONDecodeError: If the file is not valid JSON.
        ValueError: If the top-level JSON value is not an object.
    """
    with open(path, "r", encoding="utf-8") as handle:
        data = json.load(handle)
    if not isinstance(data, dict):
        raise ValueError(f"Subway data file '{path}' must contain a JSON object")
    data.setdefault("stations", [])
    data.setdefault("connections", [])
    return data
