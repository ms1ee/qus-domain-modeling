"""Central configuration for the food delivery dispatch simulator.

Module-level constants describe the fixed map geometry. ``SETTINGS`` holds
tunable parameters that can be overridden through a JSON configuration file
loaded with :func:`load_config`.
"""

import json
import logging
import os

logger = logging.getLogger(__name__)

# Map geometry: an 800x800 unit plane split into 8x8 cells of 100x100 units.
MAP_SIZE = 800
CELL_SIZE = 100
GRID_SIZE = 8
COORD_MIN = 0
COORD_MAX = MAP_SIZE

# Street intersection where newly recruited riders appear.
HUB_POSITION = (400, 400)

DEFAULT_CONFIG_PATH = "dispatch_config.json"
DEFAULT_STATE_PATH = "dispatch_state.json"
HISTORY_SIZE = 100
MAX_TICKS_PER_COMMAND = 10000

# Tunable parameters. Any of these may be overridden by the JSON config file.
SETTINGS = {
    "initial_funds": 300,
    "rider_hire_threshold": 300,
    "rider_hire_cost": 300,
    "order_fee": 120,
    "default_rider_speed": 50,
    "max_orders_per_rider": 3,
    "load_penalty": 100,
    "max_wait_ticks": 3,
}

_POSITIVE_KEYS = {"default_rider_speed", "max_orders_per_rider"}


def load_config(path=DEFAULT_CONFIG_PATH):
    """Load tunable settings from a JSON file, if it exists.

    The file may either be a flat object of setting names to integers or an
    object with a ``"settings"`` key containing such an object. Unknown or
    invalid entries are logged and ignored; the defaults remain in effect.

    Args:
        path: Path to the JSON configuration file.

    Returns:
        A copy of the effective settings dictionary.
    """
    if not os.path.exists(path):
        logger.info("No configuration file at %s; using defaults", path)
        return dict(SETTINGS)

    try:
        with open(path, "r", encoding="utf-8") as handle:
            data = json.load(handle)
    except (OSError, ValueError) as exc:
        logger.error("Could not read configuration %s: %s", path, exc)
        return dict(SETTINGS)

    if not isinstance(data, dict):
        logger.error("Configuration %s must contain a JSON object", path)
        return dict(SETTINGS)

    params = data.get("settings", data)
    if not isinstance(params, dict):
        logger.error("'settings' in %s must be a JSON object", path)
        return dict(SETTINGS)

    for key, value in params.items():
        if key not in SETTINGS:
            logger.warning("Unknown configuration key ignored: %s", key)
            continue
        if not isinstance(value, int) or isinstance(value, bool):
            logger.warning("Configuration key %s must be an integer", key)
            continue
        if key in _POSITIVE_KEYS and value <= 0:
            logger.warning("Configuration key %s must be positive", key)
            continue
        SETTINGS[key] = value

    logger.info("Configuration loaded from %s", path)
    return dict(SETTINGS)
