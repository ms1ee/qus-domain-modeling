"""Data loading utilities for the Beijing Subway fare calculation system."""

import json
import os

# Absolute path of the bundled data file, valid regardless of working directory.
DATA_FILE_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "subway_data.json")


def load_subway_data(path=DATA_FILE_PATH):
    """Load and return the JSON content of the subway data file.

    Raises FileNotFoundError if the file does not exist and ValueError if
    the content is not valid JSON.
    """
    if path is None:
        path = DATA_FILE_PATH
    with open(path, "r", encoding="utf-8") as fh:
        try:
            return json.load(fh)
        except json.JSONDecodeError as exc:
            raise ValueError(f"Invalid JSON in data file '{path}': {exc}") from exc
