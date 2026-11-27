"""Loading of the Beijing Subway network dataset.

The dataset is stored in ``subway_data.json`` located next to this module, so the
loader works regardless of the current working directory.
"""

import json
import os

# Absolute path of the subway dataset, valid from any working directory.
DATA_FILE_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "subway_data.json")


def load_subway_data(path=DATA_FILE_PATH):
    """Load the subway dataset from a JSON file.

    Args:
        path: Path of the JSON file. Defaults to ``DATA_FILE_PATH``.

    Returns:
        dict: The JSON content, containing at least the ``stations`` and
        ``connections`` lists.

    Raises:
        FileNotFoundError: If the file does not exist.
        ValueError: If the file is not valid JSON or has an invalid structure.
    """
    try:
        with open(path, "r", encoding="utf-8") as handle:
            data = json.load(handle)
    except FileNotFoundError as exc:
        raise FileNotFoundError("Subway data file not found: %s" % path) from exc
    except json.JSONDecodeError as exc:
        raise ValueError("Subway data file is not valid JSON: %s (%s)" % (path, exc)) from exc

    if not isinstance(data, dict):
        raise ValueError("Subway data root must be a JSON object: %s" % path)
    for key in ("stations", "connections"):
        if key not in data or not isinstance(data[key], list):
            raise ValueError("Subway data is missing the list '%s': %s" % (key, path))
    return data
