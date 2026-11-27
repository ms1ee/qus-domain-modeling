"""Loading of the Beijing Subway network dataset.

The dataset lives in ``subway_data.json`` next to this module, so the path
resolves correctly regardless of the current working directory.
"""

import json
import os
from typing import Any, Dict

DATA_FILE_PATH: str = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "subway_data.json"
)

REQUIRED_TOP_LEVEL_KEYS = ("stations", "connections")


def load_subway_data(path: str = DATA_FILE_PATH) -> Dict[str, Any]:
    """Load and minimally validate the subway dataset.

    Args:
        path: Path of the JSON data file. Defaults to ``DATA_FILE_PATH``.

    Returns:
        The decoded JSON content as a dictionary.

    Raises:
        OSError: If the file cannot be read.
        ValueError: If the content is not valid JSON or lacks required keys.
    """
    with open(path, "r", encoding="utf-8") as handle:
        data = json.load(handle)

    if not isinstance(data, dict):
        raise ValueError("Subway data must be a JSON object")
    for key in REQUIRED_TOP_LEVEL_KEYS:
        if key not in data:
            raise ValueError(f"Subway data is missing required key '{key}'")
        if not isinstance(data[key], list):
            raise ValueError(f"Subway data key '{key}' must be a list")
    return data
