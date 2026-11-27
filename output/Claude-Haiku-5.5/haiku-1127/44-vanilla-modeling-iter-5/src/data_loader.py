"""Loading of the Beijing Subway network dataset from JSON.

The dataset file lives next to this module (``src/subway_data.json``), so the
path resolves correctly regardless of the current working directory.
"""

import json
import os

DATA_FILE_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "subway_data.json")


def load_subway_data(path):
    """Load the subway dataset JSON file and return its content as a dict.

    Args:
        path: Path to the JSON file containing ``stations`` and ``connections``.

    Returns:
        dict: The parsed JSON object.

    Raises:
        OSError: If the file cannot be read.
        ValueError: If the JSON is malformed or not a JSON object.
    """
    with open(path, "r", encoding="utf-8") as handle:
        data = json.load(handle)
    if not isinstance(data, dict):
        raise ValueError("subway data file must contain a JSON object at the top level")
    return data
