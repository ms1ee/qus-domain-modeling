"""Configuration parameters for the food delivery dispatch simulator.

Values can be overridden through a JSON configuration file (see
:func:`load_config`).  Keys in the JSON file are case-insensitive and map
to the module level constants defined below.
"""

import json
import logging
import os

logger = logging.getLogger(__name__)

# Map / grid
GRID_SIZE = 100          # size of one grid cell in units
MAP_SIZE = 800           # map size in units
GRID_CELLS = 8           # number of cells per side

# Economy
INITIAL_FUNDS = 300      # funds available at system start
RIDER_COST = 300         # cost of recruiting a rider (trigger threshold)
ORDER_FEE = 100          # income credited when an order is delivered
MAX_RIDERS = 50          # safety cap on automatic recruitment

# Riders
RIDER_SPEED = 50         # units per tick
RIDER_START_X = 400      # spawn position (street intersection)
RIDER_START_Y = 400

# Files
STATE_FILE = "dispatch_state.json"
CONFIG_FILE = "config.json"

_CONFIGURABLE = (
    "INITIAL_FUNDS", "RIDER_COST", "ORDER_FEE", "MAX_RIDERS",
    "RIDER_SPEED", "RIDER_START_X", "RIDER_START_Y", "STATE_FILE",
)


def load_config(path=None):
    """Load configuration overrides from a JSON file.

    :param path: path of the JSON file (defaults to ``CONFIG_FILE``).
    :return: True if a file was loaded, False otherwise.
    """
    path = path or CONFIG_FILE
    if not os.path.exists(path):
        return False
    try:
        with open(path, "r", encoding="utf-8") as fh:
            data = json.load(fh)
    except (OSError, ValueError) as exc:
        logger.warning("Could not read config file %s: %s", path, exc)
        return False
    if not isinstance(data, dict):
        return False
    params = data.get("system", data)
    if not isinstance(params, dict):
        return False
    for key, value in params.items():
        name = str(key).upper()
        if name in _CONFIGURABLE:
            current = globals()[name]
            try:
                globals()[name] = type(current)(value)
            except (TypeError, ValueError):
                logger.warning("Invalid value for %s: %r", name, value)
    return True
