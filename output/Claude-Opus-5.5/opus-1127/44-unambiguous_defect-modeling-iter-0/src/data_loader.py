"""Loading of the Beijing Subway network data file (``subway_data.json``)."""

import json
import os

# Absolute path of the bundled data file, valid from any working directory.
DATA_FILE_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "subway_data.json")


def load_subway_data(path=DATA_FILE_PATH):
    """Load and return the JSON content of the subway data file.

    :param path: path of the JSON file (defaults to ``DATA_FILE_PATH``).
    :return: the parsed JSON content (a dict with ``stations`` and
             ``connections`` keys).
    :raises FileNotFoundError: if the file does not exist.
    :raises ValueError: if the file is not valid JSON or not a JSON object.
    """
    if path is None:
        path = DATA_FILE_PATH
    with open(path, "r", encoding="utf-8") as handle:
        data = json.load(handle)
    if not isinstance(data, dict):
        raise ValueError("Subway data file must contain a JSON object")
    return data
