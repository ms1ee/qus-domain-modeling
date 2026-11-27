"""Loading of the Beijing Subway network dataset.

The dataset lives in ``subway_data.json`` next to this module. The path is
resolved relative to this file so the program works from any working directory.
"""

import json
import os

DATA_FILE_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "subway_data.json")


def load_subway_data(path=DATA_FILE_PATH):
    """Load the subway dataset from a JSON file.

    Args:
        path: Path to the JSON file. Defaults to ``DATA_FILE_PATH``.

    Returns:
        dict with the keys ``stations`` and ``connections`` (missing keys are
        filled with empty lists).

    Raises:
        FileNotFoundError: If the file does not exist.
        ValueError: If the file does not contain a valid JSON object.
    """
    if not os.path.isfile(path):
        raise FileNotFoundError(f"Subway data file not found: {path}")
    with open(path, "r", encoding="utf-8") as handle:
        try:
            data = json.load(handle)
        except json.JSONDecodeError as exc:
            raise ValueError(f"Subway data file is not valid JSON: {exc}") from exc
    if not isinstance(data, dict):
        raise ValueError("Subway data file must contain a JSON object")
    data.setdefault("stations", [])
    data.setdefault("connections", [])
    return data
