"""Data loading utilities for the Beijing Subway network dataset.

The dataset is stored in ``subway_data.json`` next to this module. The path is
resolved from the location of this file, so the program can be started from
any working directory.
"""

import json
import os
from typing import Any, Dict, List

# Absolute path of src/subway_data.json, valid regardless of the working directory.
DATA_FILE_PATH: str = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "subway_data.json"
)

# Top-level keys that every subway dataset must provide.
REQUIRED_KEYS = ("stations", "connections")


def load_subway_data(path: str) -> dict:
    """Load the subway network dataset from a JSON file.

    Args:
        path: Path of the JSON file to read.

    Returns:
        The parsed JSON content as a dictionary with the keys
        ``stations`` and ``connections``.

    Raises:
        OSError: If the file cannot be opened.
        ValueError: If the JSON content does not follow the expected structure.
    """
    with open(path, "r", encoding="utf-8") as handle:
        data: Any = json.load(handle)

    if not isinstance(data, dict):
        raise ValueError(f"Subway data in '{path}' must be a JSON object")

    for key in REQUIRED_KEYS:
        if key not in data:
            raise ValueError(f"Subway data in '{path}' is missing the key '{key}'")
        if not isinstance(data[key], list):
            raise ValueError(f"Key '{key}' in '{path}' must be a JSON array")

    return data


def save_subway_data(data: dict, path: str) -> None:
    """Persist the subway network dataset to a JSON file.

    Args:
        data: Dataset dictionary with ``stations`` and ``connections`` keys.
        path: Destination file path. Missing parent directories are created.
    """
    directory = os.path.dirname(os.path.abspath(path))
    os.makedirs(directory, exist_ok=True)
    with open(path, "w", encoding="utf-8") as handle:
        json.dump(data, handle, ensure_ascii=False, indent=2)
        handle.write("\n")


def list_required_keys() -> List[str]:
    """Return the top-level keys required in the dataset file."""
    return list(REQUIRED_KEYS)


def describe_dataset(data: Dict[str, Any]) -> str:
    """Return a short human-readable summary of a loaded dataset."""
    return (
        f"{len(data.get('stations', []))} station records, "
        f"{len(data.get('connections', []))} connection records"
    )
