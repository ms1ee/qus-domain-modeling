"""Configuration constants and optional JSON configuration loading.

All map geometry and default system parameters live here so that every
other module shares one source of truth.
"""

import json
import logging
import os
from typing import Any, Dict

logger = logging.getLogger("dispatch.config")

# Map geometry (units).
MAP_SIZE = 800          # Map is 800x800 units.
CELL_SIZE = 100         # Each grid cell is 100x100 units.
GRID_CELLS = 8          # 8x8 cells (64 total).

# Rider defaults.
RIDER_START_X = 400
RIDER_START_Y = 400
RIDER_SPEED = 20        # Units per tick.

# User input bounds (validated on input; values above MAP_SIZE snap to the edge).
INPUT_MIN = 0
INPUT_MAX = 1000

# Simulation safety limit when running an order to completion.
MAX_TICKS_PER_ORDER = 10000

# File names.
DEFAULT_CONFIG_PATH = "dispatch_config.json"
DEFAULT_STATE_PATH = "dispatch_state.json"

# Tunable system parameters (overridable via JSON configuration file).
DEFAULTS: Dict[str, int] = {
    "initial_funds": 1000,
    "recruit_min_funds": 300,
    "recruit_cost": 500,
    "rider_speed": RIDER_SPEED,
    "max_ticks_per_order": MAX_TICKS_PER_ORDER,
}


def load_config(path: str = DEFAULT_CONFIG_PATH) -> Dict[str, Any]:
    """Load system parameters from a JSON file, falling back to defaults.

    Unknown keys are ignored. Invalid values produce a warning and keep the
    default. A missing or unreadable file yields the default parameters.

    Args:
        path: Path to the JSON configuration file.

    Returns:
        A dictionary containing every key from ``DEFAULTS``.
    """
    params: Dict[str, Any] = dict(DEFAULTS)
    if not os.path.isfile(path):
        return params
    try:
        with open(path, "r", encoding="utf-8") as handle:
            data = json.load(handle)
    except (OSError, json.JSONDecodeError) as exc:
        logger.warning("Could not read configuration %s: %s", path, exc)
        return params
    if not isinstance(data, dict):
        logger.warning("Configuration %s must contain a JSON object", path)
        return params
    for key in DEFAULTS:
        if key in data:
            try:
                params[key] = int(data[key])
            except (TypeError, ValueError):
                logger.warning("Invalid value for %s in %s; using default", key, path)
    return params
