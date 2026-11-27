"""System parameter defaults and optional JSON configuration loading.

Parameters can be customised by placing a JSON object in
``dispatch_config.json`` in the working directory. Unknown keys and keys
with the wrong value type are ignored with a warning.
"""

import copy
import json
import logging
import os
from typing import Any, Dict

logger = logging.getLogger(__name__)

CONFIG_FILE = "dispatch_config.json"

DEFAULT_CONFIG: Dict[str, Any] = {
    "initial_funds": 300,
    "recruit_threshold": 300,
    "recruit_cost": 300,
    "delivery_fee": 100,
    "default_rider_speed": 50,
    "load_penalty": 100,
    "max_ticks_per_order": 5000,
    "save_file": "dispatch_state.json",
    "log_file": "dispatch.log",
    "log_level": "INFO",
}


def load_config(path: str = CONFIG_FILE) -> Dict[str, Any]:
    """Load system parameters, falling back to defaults on any problem.

    Args:
        path: Path of the JSON configuration file.

    Returns:
        A dictionary containing every known configuration key.
    """
    config = copy.deepcopy(DEFAULT_CONFIG)
    if not os.path.exists(path):
        return config
    try:
        with open(path, "r", encoding="utf-8") as handle:
            data = json.load(handle)
    except (OSError, json.JSONDecodeError) as exc:
        logger.warning("Could not read config %s: %s; using defaults", path, exc)
        return config
    if not isinstance(data, dict):
        logger.warning("Config %s must contain a JSON object; using defaults", path)
        return config
    for key, value in data.items():
        if key not in DEFAULT_CONFIG:
            logger.warning("Ignoring unknown config key '%s'", key)
            continue
        expected = type(DEFAULT_CONFIG[key])
        if not isinstance(value, expected):
            logger.warning("Config key '%s' must be of type %s; ignored",
                           key, expected.__name__)
            continue
        config[key] = value
    return config
