"""Loading of the Beijing Subway raw dataset from ``subway_data.json``."""
from __future__ import annotations

import json
import os

# Absolute path of src/subway_data.json, valid regardless of the working directory.
DATA_FILE_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "subway_data.json")


def load_subway_data(path: str) -> dict:
    """Load and minimally validate the subway dataset.

    Args:
        path: Path of the JSON data file.

    Returns:
        The JSON content as a dictionary with ``stations`` and ``connections`` lists.

    Raises:
        FileNotFoundError: If the file does not exist.
        ValueError: If the content is not valid JSON or does not have the expected structure.
    """
    if not os.path.isfile(path):
        raise FileNotFoundError(f"subway data file not found: {path}")

    with open(path, "r", encoding="utf-8") as fh:
        try:
            data = json.load(fh)
        except json.JSONDecodeError as exc:
            raise ValueError(f"subway data file is not valid JSON: {exc}") from exc

    if not isinstance(data, dict):
        raise ValueError("subway data must be a JSON object")
    for key in ("stations", "connections"):
        if not isinstance(data.get(key), list):
            raise ValueError(f"subway data must contain a list under key '{key}'")
    return data
