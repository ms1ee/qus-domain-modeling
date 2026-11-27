"""System configuration parameters.

Defaults are defined in ``DEFAULT_CONFIG``. An optional JSON file may override
any subset of these keys. Values are validated before they are applied, and an
invalid file never leaves the configuration in an unusable state.
"""

import json
import logging
from typing import Dict

logger = logging.getLogger("dispatch")

DEFAULT_CONFIG: Dict[str, int] = {
    "map_size": 800,            # map width/height in coordinate units
    "cell_size": 100,           # size of one grid cell in units
    "rider_speed": 25,          # units a rider moves per tick
    "initial_funds": 300,       # system funds at startup
    "hire_threshold": 300,      # funds required to recruit a rider
    "hire_cost": 300,           # funds consumed by each recruitment
    "delivery_fee": 100,        # funds earned per completed delivery
    "max_orders_per_rider": 3,  # maximum queued orders per rider
    "load_penalty": 200,        # distance penalty added per queued order
    "turn_penalty": 1,          # extra path cost for a right-angle turn
}

# Minimum accepted value for each configurable key.
MINIMUMS: Dict[str, int] = {
    "map_size": 1,
    "cell_size": 1,
    "rider_speed": 1,
    "initial_funds": 0,
    "hire_threshold": 0,
    "hire_cost": 1,
    "delivery_fee": 0,
    "max_orders_per_rider": 1,
    "load_penalty": 0,
    "turn_penalty": 0,
}

# Live configuration. Modules read values from this dict at call time, so a
# JSON override loaded at startup is visible everywhere.
CONFIG: Dict[str, int] = dict(DEFAULT_CONFIG)


def load_config(path: str) -> Dict[str, int]:
    """Load configuration overrides from a JSON file.

    The file may either contain the keys directly or nest them under a
    ``"system"`` object. Missing files are not an error; defaults are used.

    Args:
        path: Path to the JSON configuration file.

    Returns:
        The live configuration dictionary (``CONFIG``).
    """
    try:
        with open(path, "r", encoding="utf-8") as handle:
            data = json.load(handle)
    except FileNotFoundError:
        logger.info("Config file %s not found; using defaults.", path)
        return CONFIG
    except (OSError, ValueError) as exc:
        logger.warning("Could not read config file %s (%s); using defaults.", path, exc)
        return CONFIG

    section = data.get("system", data) if isinstance(data, dict) else None
    if not isinstance(section, dict):
        logger.warning("Config file %s has an unexpected structure; using defaults.", path)
        return CONFIG

    for key, minimum in MINIMUMS.items():
        if key not in section:
            continue
        value = section[key]
        if isinstance(value, bool) or not isinstance(value, int) or value < minimum:
            logger.warning("Ignoring invalid value for %s: %r", key, value)
            continue
        CONFIG[key] = value

    if CONFIG["map_size"] % CONFIG["cell_size"] != 0:
        logger.warning("map_size must be a multiple of cell_size; restoring defaults.")
        CONFIG.update(DEFAULT_CONFIG)

    return CONFIG
