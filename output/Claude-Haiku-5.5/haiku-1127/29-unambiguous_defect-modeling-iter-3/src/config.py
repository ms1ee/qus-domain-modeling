"""Configuration loading and JSON persistence helpers."""

import copy
import json
import logging
import os

logger = logging.getLogger(__name__)

DEFAULT_CONFIG = {
    "initial_funds": 5000,
    "recruitment_cost": 800,
    "max_riders": 10,
    "rider_capacity": 2,
    "load_penalty": 150,
    "speed_options": [10, 15, 20],
    "state_file": "dispatch_state.json",
}


def load_json(path):
    """Read and parse a JSON file.

    Args:
        path: File path to read.

    Returns:
        The parsed JSON object.

    Raises:
        OSError: If the file cannot be read.
        ValueError: If the content is not valid JSON.
    """
    with open(path, "r", encoding="utf-8") as handle:
        return json.load(handle)


def save_json(path, data):
    """Write ``data`` to ``path`` as formatted JSON.

    Args:
        path: Destination file path.
        data: JSON-serialisable object.

    Raises:
        OSError: If the file cannot be written.
    """
    with open(path, "w", encoding="utf-8") as handle:
        json.dump(data, handle, indent=2, ensure_ascii=False)


def load_config(path=None):
    """Load system parameters, falling back to defaults for anything invalid.

    Args:
        path: Optional path to a JSON configuration file.

    Returns:
        dict: Complete configuration dictionary.
    """
    config = copy.deepcopy(DEFAULT_CONFIG)
    if not path:
        return config
    if not os.path.exists(path):
        logger.warning("Config file %s not found; using defaults.", path)
        return config
    try:
        data = load_json(path)
    except (OSError, ValueError) as exc:
        logger.error("Could not read config %s: %s; using defaults.", path, exc)
        return config
    if not isinstance(data, dict):
        logger.error("Config %s must contain a JSON object; using defaults.", path)
        return config

    for key in DEFAULT_CONFIG:
        if key not in data:
            continue
        value = data[key]
        if key == "speed_options":
            if (isinstance(value, list) and value
                    and all(isinstance(v, int) and not isinstance(v, bool) and v > 0
                            for v in value)):
                config[key] = value
            else:
                logger.warning("Invalid speed_options in config; keeping default.")
        elif key == "state_file":
            if isinstance(value, str) and value:
                config[key] = value
            else:
                logger.warning("Invalid state_file in config; keeping default.")
        else:
            if isinstance(value, int) and not isinstance(value, bool) and value >= 0:
                config[key] = value
            else:
                logger.warning("Invalid value for %s in config; keeping default.", key)
    return config
