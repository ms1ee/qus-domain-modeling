"""Loading of the subway network data file."""

import json
import os

DATA_FILE_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "subway_data.json")


def load_subway_data(path=DATA_FILE_PATH):
    """Load and return the JSON content of the subway data file.

    Raises:
        FileNotFoundError / OSError if the file cannot be read.
        ValueError if the content is not valid JSON or has a bad structure.
    """
    if path is None:
        path = DATA_FILE_PATH
    with open(path, "r", encoding="utf-8") as handle:
        data = json.load(handle)
    if not isinstance(data, dict):
        raise ValueError("Subway data must be a JSON object")
    data.setdefault("stations", [])
    data.setdefault("connections", [])
    if not isinstance(data["stations"], list) or not isinstance(data["connections"], list):
        raise ValueError("'stations' and 'connections' must be lists")
    return data


def build_network(data=None, path=DATA_FILE_PATH):
    """Convenience helper returning a ``SubwayNetwork`` built from data."""
    from data_manager import SubwayNetwork

    if data is None:
        data = load_subway_data(path)
    return SubwayNetwork(data)
