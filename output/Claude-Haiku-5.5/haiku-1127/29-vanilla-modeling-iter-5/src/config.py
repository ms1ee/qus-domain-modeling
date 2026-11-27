"""System configuration loading.

Parameters can be customised through a JSON file. Keys missing from the file
fall back to the defaults defined in ``DEFAULT_CONFIG``.
"""

import json
import logging
import os
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)

DEFAULT_CONFIG: Dict[str, Any] = {
    "initial_funds": 1000,
    "rider_cost": 300,
    "recruit_min_funds": 300,
    "rider_start_x": 435,
    "rider_start_y": 385,
    "rider_speed": 10,
    "max_orders_per_rider": 3,
    "max_ticks_per_order": 2000,
    "log_level": "WARNING",
    "state_file": "state.json",
}

DEFAULT_CONFIG_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "config.json",
)

CONFIG: Dict[str, Any] = dict(DEFAULT_CONFIG)


def load_config(path: Optional[str] = None) -> Dict[str, Any]:
    """Load system parameters from a JSON file.

    Args:
        path: Optional path to a JSON configuration file. When omitted the
            ``config.json`` file in the project root is used if it exists.

    Returns:
        The active configuration dictionary.
    """
    CONFIG.clear()
    CONFIG.update(DEFAULT_CONFIG)
    target = path or DEFAULT_CONFIG_PATH
    if not os.path.exists(target):
        if path:
            logger.warning("Configuration file not found: %s; using defaults", path)
        return CONFIG
    try:
        with open(target, "r", encoding="utf-8") as handle:
            data = json.load(handle)
    except (OSError, json.JSONDecodeError) as exc:
        logger.warning("Could not read configuration %s: %s", target, exc)
        return CONFIG
    if isinstance(data, dict):
        for key in DEFAULT_CONFIG:
            if key in data:
                CONFIG[key] = data[key]
    else:
        logger.warning("Configuration file %s must contain a JSON object", target)
    return CONFIG
