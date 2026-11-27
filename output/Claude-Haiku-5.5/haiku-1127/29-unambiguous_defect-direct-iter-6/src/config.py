"""System constants, default configuration, and configuration loading.

Grid conventions used throughout the program:

* The map is 800x800 units (``MAP_SIZE``) with integer coordinates 0-800.
* Each 100x100 cell (``CELL_SIZE``) has its centre at ``(n * 100) + 50``.
  Cell centres are restaurant/customer locations.
* Streets are the grid lines where ``x % 100 == 0`` or ``y % 100 == 0``.
* Movement happens on a lattice with a spacing of ``LATTICE_STEP`` (50)
  units, so every point is either a street point or a cell-centre location.
"""

import json
import logging

import globalvar

logger = logging.getLogger(__name__)

MAP_SIZE = 800
CELL_SIZE = 100
GRID_SIZE = 8
LATTICE_STEP = 50
COORD_MIN = 0
COORD_MAX = MAP_SIZE
SPEED_CHOICES = (50, 100)

DEFAULT_CONFIG = {
    "initial_funds": 10000,
    "rider_cost": 500,
    "max_riders": 12,
    "min_riders": 2,
    "delivery_fee": 60,
    "load_penalty": 100,
    "state_file": "dispatch_state.json",
    "log_file": "dispatch.log",
}


def load_config(path=None):
    """Load system parameters, merging a JSON file over the defaults.

    Unknown keys and keys with a value of the wrong type are ignored with a
    warning. A missing or malformed file falls back to the defaults.

    Args:
        path: Optional path to a JSON configuration file.

    Returns:
        A new dictionary containing every configuration key.
    """
    cfg = dict(DEFAULT_CONFIG)
    if path is None:
        return cfg
    try:
        with open(path, encoding="utf-8") as handle:
            data = json.load(handle)
    except FileNotFoundError:
        logger.warning("Configuration file %s not found; using defaults", path)
        return cfg
    except (OSError, json.JSONDecodeError) as exc:
        logger.error("Cannot read configuration file %s: %s", path, exc)
        return cfg
    if not isinstance(data, dict):
        logger.error("Configuration file %s must contain a JSON object", path)
        return cfg
    for key, value in data.items():
        if key in DEFAULT_CONFIG and type(value) is type(DEFAULT_CONFIG[key]):
            cfg[key] = value
        else:
            logger.warning("Ignoring configuration key %r", key)
    return cfg


def setting(key):
    """Return a configuration value from the active configuration.

    Args:
        key: Name of the configuration parameter.

    Returns:
        The active value, or the default value if none is loaded.
    """
    cfg = globalvar.get_value("config") or DEFAULT_CONFIG
    return cfg.get(key, DEFAULT_CONFIG[key])
