"""Data loading utilities for the Beijing Subway fare calculation system.

The network data lives in ``subway_data.json`` next to this module.  The
file has the following layout::

    {"stations": [{"name": str, "lines": [str]}],
     "connections": [{"source": str, "dest": str,
                      "distance": int, "line": str}]}
"""

import json
import os

# Absolute path of the bundled data file; valid from any working directory.
DATA_FILE_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                              "subway_data.json")


def load_subway_data(path=DATA_FILE_PATH):
    """Load and return the JSON content of the subway data file.

    :param path: path to the JSON file (defaults to ``DATA_FILE_PATH``)
    :return: the parsed JSON content (a dict)
    :raises FileNotFoundError: if the file does not exist
    :raises ValueError: if the file content is not valid JSON / not a dict
    """
    if path is None:
        path = DATA_FILE_PATH
    with open(path, "r", encoding="utf-8") as fh:
        data = json.load(fh)
    if not isinstance(data, dict):
        raise ValueError("Subway data file must contain a JSON object")
    data.setdefault("stations", [])
    data.setdefault("connections", [])
    return data
