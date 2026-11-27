"""Loading of the Beijing Subway network dataset (src/subway_data.json)."""

import json
import os

# Absolute path of the dataset, resolved relative to this file so that the
# program works from any current working directory.
DATA_FILE_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "subway_data.json")


def load_subway_data(path: str = DATA_FILE_PATH) -> dict:
    """Load and return the raw JSON content of the subway dataset.

    The returned dictionary has the form:
        {"stations": [{"name": str, "lines": [str]}],
         "connections": [{"source": str, "dest": str, "distance": int, "line": str}]}

    Raises:
        FileNotFoundError: if the file does not exist.
        ValueError: if the JSON content does not have the expected structure.
    """
    if not os.path.isfile(path):
        raise FileNotFoundError(f"Subway data file not found: {path}")

    with open(path, "r", encoding="utf-8") as handle:
        try:
            data = json.load(handle)
        except json.JSONDecodeError as exc:
            raise ValueError(f"Subway data file is not valid JSON: {exc}") from exc

    if not isinstance(data, dict):
        raise ValueError("Subway data must be a JSON object")
    if not isinstance(data.get("stations"), list):
        raise ValueError("Subway data must contain a 'stations' list")
    if not isinstance(data.get("connections"), list):
        raise ValueError("Subway data must contain a 'connections' list")
    return data
