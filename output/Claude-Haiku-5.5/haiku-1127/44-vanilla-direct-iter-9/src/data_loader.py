"""Loading of the Beijing Subway network dataset.

The dataset lives in ``subway_data.json`` next to this module. The path is
resolved relative to this file so the program works from any working
directory.
"""

import json
import os
from typing import Any, Dict

DATA_FILE_PATH: str = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "subway_data.json"
)

REQUIRED_KEYS = ("stations", "connections")


def load_subway_data(path: str) -> Dict[str, Any]:
    """Load the subway dataset from a JSON file.

    Args:
        path: Path to the JSON file containing ``stations`` and ``connections``.

    Returns:
        The parsed JSON content as a dictionary.

    Raises:
        OSError: If the file cannot be opened.
        ValueError: If the JSON is malformed or lacks the required structure.
    """
    with open(path, "r", encoding="utf-8") as handle:
        data = json.load(handle)

    if not isinstance(data, dict):
        raise ValueError("Subway data file must contain a JSON object")

    for key in REQUIRED_KEYS:
        if not isinstance(data.get(key), list):
            raise ValueError(f"Subway data file must contain a list under '{key}'")

    return data
