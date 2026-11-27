"""Data loading utilities for the Beijing Subway network.

The subway network dataset is stored in ``subway_data.json`` located in the
same directory as this module, so it can be loaded from any working directory.
"""

from __future__ import annotations

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
        path: Path to the JSON data file.

    Returns:
        The parsed JSON content as a dictionary with the keys
        ``stations`` and ``connections``.

    Raises:
        OSError: If the file cannot be read.
        ValueError: If the JSON is malformed or lacks the required structure.
    """
    with open(path, "r", encoding="utf-8") as handle:
        try:
            data = json.load(handle)
        except json.JSONDecodeError as exc:
            raise ValueError(f"Invalid JSON in '{path}': {exc}") from exc

    if not isinstance(data, dict):
        raise ValueError("Subway data must be a JSON object")

    for key in REQUIRED_TOP_LEVEL_KEYS:
        if key not in data:
            raise ValueError(f"Subway data is missing the '{key}' section")
        if not isinstance(data[key], list):
            raise ValueError(f"Subway data section '{key}' must be a list")

    return data
