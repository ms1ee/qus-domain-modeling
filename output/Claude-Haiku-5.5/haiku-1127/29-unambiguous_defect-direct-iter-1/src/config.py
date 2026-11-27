"""System configuration parameters.

Default values can be overridden by a JSON configuration file loaded with
:func:`load_config`. Only keys that exist in :data:`DEFAULTS` are accepted.
"""

import json
import logging

logger = logging.getLogger(__name__)

GRID_SIZE = 800
CELL_SIZE = 100

DEFAULTS = {
    "initial_funds": 2000,
    "recruit_cost": 300,
    "max_riders": 10,
    "max_orders_per_rider": 3,
    "load_weight": 150,
    "rider_speeds": [50, 75, 100],
}

CONFIG = dict(DEFAULTS)


def load_config(path):
    """Load configuration overrides from a JSON file.

    Args:
        path: Path to a JSON file containing a single object whose keys are
            configuration names.

    Returns:
        dict: A copy of the effective configuration after applying overrides.
    """
    try:
        with open(path, "r", encoding="utf-8") as handle:
            data = json.load(handle)
    except (OSError, ValueError) as exc:
        logger.error("Could not load configuration '%s': %s", path, exc)
        return dict(CONFIG)

    if not isinstance(data, dict):
        logger.error("Configuration file '%s' must contain a JSON object", path)
        return dict(CONFIG)

    for key, value in data.items():
        if key not in DEFAULTS:
            logger.warning("Unknown configuration key ignored: %s", key)
            continue
        if key == "rider_speeds":
            if not isinstance(value, list) or not value:
                logger.warning("Invalid rider_speeds ignored")
                continue
        CONFIG[key] = value
    logger.info("Configuration loaded from %s", path)
    return dict(CONFIG)
