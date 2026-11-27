"""Loading of the Beijing Subway network dataset.

The dataset file ``subway_data.json`` lives next to this module, so the
default path works regardless of the current working directory.
"""

import json
import os

DATA_FILE_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "subway_data.json")


def load_subway_data(path):
    """Load the subway dataset from a JSON file.

    Args:
        path: Path to the JSON file. Expected structure::

            {"stations": [{"name": str, "lines": [str]}],
             "connections": [{"source": str, "dest": str,
                              "distance": int, "line": str}]}

    Returns:
        dict: The parsed JSON content.

    Raises:
        OSError: If the file cannot be read.
        ValueError: If the content is not valid JSON or has an invalid structure.
    """
    with open(path, "r", encoding="utf-8") as fh:
        data = json.load(fh)

    if not isinstance(data, dict):
        raise ValueError("Subway data must be a JSON object")
    for key in ("stations", "connections"):
        if key in data and not isinstance(data[key], list):
            raise ValueError(f"Subway data field '{key}' must be a list")
    return data
