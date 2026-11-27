"""Loading of the Beijing Subway network dataset (subway_data.json)."""

import json
import os

# Absolute path of the bundled data file; valid regardless of the current working directory.
DATA_FILE_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "subway_data.json")


def load_subway_data(path=DATA_FILE_PATH):
    """Load the subway network JSON file.

    Args:
        path: path to the JSON file (defaults to DATA_FILE_PATH).

    Returns:
        dict with keys "stations" and "connections" (missing keys are filled with empty lists).

    Raises:
        OSError: if the file cannot be read.
        ValueError: if the JSON content is malformed or not an object.
    """
    with open(path, "r", encoding="utf-8") as handle:
        try:
            data = json.load(handle)
        except json.JSONDecodeError as exc:
            raise ValueError(f"Invalid JSON in subway data file '{path}': {exc}") from exc

    if not isinstance(data, dict):
        raise ValueError("Subway data file must contain a JSON object at top level")

    data.setdefault("stations", [])
    data.setdefault("connections", [])
    if not isinstance(data["stations"], list) or not isinstance(data["connections"], list):
        raise ValueError("'stations' and 'connections' must be JSON arrays")
    return data
