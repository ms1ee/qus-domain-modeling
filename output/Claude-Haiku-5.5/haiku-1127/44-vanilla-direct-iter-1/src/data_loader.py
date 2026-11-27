"""Loading of the Beijing Subway network dataset.

The dataset lives in ``subway_data.json`` next to this module, so it can be
located correctly no matter which directory the program is started from.
"""

import json
import os

# Absolute path of src/subway_data.json, valid from any working directory.
DATA_FILE_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "subway_data.json")


class DataLoadError(Exception):
    """Raised when the subway dataset cannot be read or has a malformed layout."""


def load_subway_data(path):
    """Load the subway dataset stored at ``path`` and return its JSON content.

    Args:
        path: File system path of the JSON dataset.

    Returns:
        dict: The parsed content, containing the keys ``stations`` and
        ``connections``.

    Raises:
        DataLoadError: If the file is missing, unreadable, not valid JSON, or
            does not contain the required top-level keys.
    """
    try:
        with open(path, "r", encoding="utf-8") as handle:
            data = json.load(handle)
    except FileNotFoundError as exc:
        raise DataLoadError(f"Subway data file not found: {path}") from exc
    except json.JSONDecodeError as exc:
        raise DataLoadError(f"Subway data file is not valid JSON: {exc}") from exc
    except OSError as exc:
        raise DataLoadError(f"Cannot read subway data file: {exc}") from exc

    if not isinstance(data, dict) or "stations" not in data or "connections" not in data:
        raise DataLoadError("Subway data must contain 'stations' and 'connections' keys")
    return data
