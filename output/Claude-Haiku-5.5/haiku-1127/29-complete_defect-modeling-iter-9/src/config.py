"""Project-wide constants and JSON configuration loading.

The module exposes fixed map geometry constants and a DEFAULT_CONFIG
dictionary of tunable system parameters. Parameters can be overridden by a
JSON configuration file via :func:`load_config`.
"""

import copy
import json
import logging
import os

LOGGER = logging.getLogger("dispatch")

# Fixed map geometry (not configurable).
MAP_SIZE = 800
CELL_SIZE = 100
GRID_SIZE = MAP_SIZE // CELL_SIZE  # 8x8 grid, 64 cells

# Fixed simulation defaults.
DEFAULT_RIDER_SPEED = 100          # units per tick
HUB_POSITION = (400, 400)          # street intersection where riders spawn
LOAD_PENALTY = 200                 # distance-equivalent penalty per queued order
MAX_HISTORY = 200                  # maximum number of remembered commands

DEFAULT_CONFIG = {
    "initial_funds": 300,
    "recruit_threshold": 300,
    "hire_cost": 300,
    "max_riders": 20,
    "rider_speed": DEFAULT_RIDER_SPEED,
    "hub_position": list(HUB_POSITION),
    "delivery_fee": 100,
    "fuel_cost_per_100_units": 5,
    "state_file": "dispatch_state.json",
    "save_on_exit": True,
}

_MIN_VALUES = {
    "recruit_threshold": 0,
    "hire_cost": 0,
    "max_riders": 1,
    "rider_speed": 1,
    "delivery_fee": 0,
    "fuel_cost_per_100_units": 0,
}


def default_config() -> dict:
    """Return a fresh deep copy of the default configuration.

    Returns:
        dict: Configuration dictionary with default values.
    """
    return copy.deepcopy(DEFAULT_CONFIG)


def _is_valid(key: str, value) -> bool:
    """Check whether a configuration value matches the expected type and range.

    Args:
        key: Configuration key name (must exist in DEFAULT_CONFIG).
        value: Candidate value loaded from JSON.

    Returns:
        bool: True if the value is acceptable.
    """
    default = DEFAULT_CONFIG[key]
    if isinstance(default, bool):
        return isinstance(value, bool)
    if isinstance(default, int):
        return (isinstance(value, int) and not isinstance(value, bool)
                and value >= _MIN_VALUES.get(key, -10 ** 12))
    if isinstance(default, str):
        return isinstance(value, str) and bool(value.strip())
    if isinstance(default, list):
        return (isinstance(value, list) and len(value) == 2
                and all(isinstance(v, int) and not isinstance(v, bool)
                        and 0 <= v <= MAP_SIZE for v in value))
    return False


def load_config(path=None) -> dict:
    """Load system parameters from a JSON file, falling back to defaults.

    Unknown keys and invalid values are ignored with a logged warning.
    A missing or malformed file never aborts startup.

    Args:
        path: Optional path to a JSON configuration file.

    Returns:
        dict: The effective configuration dictionary.
    """
    config = default_config()
    if path is None:
        return config
    if not os.path.exists(path):
        LOGGER.warning("Config file %s not found; using defaults", path)
        return config
    try:
        with open(path, "r", encoding="utf-8") as handle:
            data = json.load(handle)
    except (OSError, ValueError) as exc:
        LOGGER.error("Could not read config file %s: %s", path, exc)
        return config
    if not isinstance(data, dict):
        LOGGER.error("Config file %s must contain a JSON object", path)
        return config
    for key, value in data.items():
        if key not in DEFAULT_CONFIG:
            LOGGER.warning("Unknown config key %r ignored", key)
            continue
        if _is_valid(key, value):
            config[key] = copy.deepcopy(value)
        else:
            LOGGER.warning("Invalid value %r for %r; using default", value, key)
    return config
