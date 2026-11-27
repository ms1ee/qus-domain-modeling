"""Loading of the Beijing Subway network dataset.

The dataset lives in ``subway_data.json`` next to this module. The path is
resolved relative to this file, so the loader works from any working directory.
"""

import json
import os

DATA_FILE_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "subway_data.json")


def load_subway_data(path=DATA_FILE_PATH):
    """Load the subway dataset and return its JSON content as a dictionary.

    Args:
        path: Path of the JSON file. Defaults to ``DATA_FILE_PATH``.

    Returns:
        dict: The parsed JSON content with ``stations`` and ``connections`` keys.

    Raises:
        OSError: If the file cannot be opened.
        ValueError: If the JSON is malformed or lacks the required top-level keys.
    """
    with open(path, "r", encoding="utf-8") as handle:
        data = json.load(handle)
    if not isinstance(data, dict):
        raise ValueError("Subway data must be a JSON object")
    for key in ("stations", "connections"):
        if key not in data:
            raise ValueError(f"Subway data is missing the '{key}' section")
    return data
