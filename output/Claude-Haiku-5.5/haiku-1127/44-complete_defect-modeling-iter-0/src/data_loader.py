"""Loading of the Beijing Subway raw dataset from ``subway_data.json``."""

import json
import os

# Absolute path of the dataset file, valid regardless of the working directory.
DATA_FILE_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "subway_data.json")


class DataLoadError(Exception):
    """Raised when the subway dataset cannot be read or is malformed."""


def load_subway_data(path=DATA_FILE_PATH):
    """Load the subway dataset and return its JSON content as a dict.

    Args:
        path: Path to the JSON file. Defaults to ``DATA_FILE_PATH``.

    Returns:
        dict with the keys ``stations`` and ``connections``.

    Raises:
        DataLoadError: if the file cannot be read, is not valid JSON, or
            does not contain a JSON object at the top level.
    """
    if not path:
        path = DATA_FILE_PATH
    try:
        with open(path, "r", encoding="utf-8") as handle:
            data = json.load(handle)
    except OSError as exc:
        raise DataLoadError("Cannot read subway data file '{}': {}".format(path, exc)) from exc
    except ValueError as exc:
        raise DataLoadError("Subway data file '{}' is not valid JSON: {}".format(path, exc)) from exc

    if not isinstance(data, dict):
        raise DataLoadError("Subway data file '{}' must contain a JSON object".format(path))
    return data
