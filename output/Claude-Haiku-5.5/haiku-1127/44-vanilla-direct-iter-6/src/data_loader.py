"""Data loading utilities for the Beijing Subway network.

The network dataset lives in ``subway_data.json`` next to this module. The
file has the structure::

    {"stations": [{"name": str, "lines": [str]}],
     "connections": [{"source": str, "dest": str, "distance": int, "line": str}]}

Distances are expressed in meters.
"""

import json
import os

# Absolute path of src/subway_data.json, valid regardless of the working directory.
DATA_FILE_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "subway_data.json")


def load_subway_data(path=DATA_FILE_PATH):
    """Load the subway dataset from a JSON file.

    Args:
        path: Path to the JSON data file. Defaults to ``DATA_FILE_PATH``.

    Returns:
        dict: The JSON content of the file with ``stations`` and
        ``connections`` keys.

    Raises:
        FileNotFoundError: If the file does not exist.
        ValueError: If the file is not valid JSON or lacks required keys.
    """
    file_path = DATA_FILE_PATH if path is None else os.fspath(path)
    try:
        with open(file_path, "r", encoding="utf-8") as handle:
            data = json.load(handle)
    except FileNotFoundError as exc:
        raise FileNotFoundError(f"Subway data file not found: {file_path}") from exc
    except json.JSONDecodeError as exc:
        raise ValueError(f"Subway data file is not valid JSON: {exc}") from exc

    if not isinstance(data, dict) or "stations" not in data or "connections" not in data:
        raise ValueError("Subway data must contain 'stations' and 'connections' keys")
    return data


def save_subway_data(data, path=DATA_FILE_PATH):
    """Write the subway dataset back to a JSON file.

    Args:
        data: The dataset dictionary.
        path: Destination file path. Defaults to ``DATA_FILE_PATH``.

    Raises:
        OSError: If the file cannot be written.
    """
    file_path = DATA_FILE_PATH if path is None else os.fspath(path)
    with open(file_path, "w", encoding="utf-8") as handle:
        json.dump(data, handle, ensure_ascii=False, indent=2)
        handle.write("\n")
