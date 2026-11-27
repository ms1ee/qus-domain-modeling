"""Global configuration constants and JSON persistence helpers.

This module holds the immutable map parameters, the default system settings,
and helpers for loading a JSON configuration file and writing the simulator
state to disk.
"""

import json
import logging
import os
from typing import Any, Dict, Optional

LOGGER = logging.getLogger("dispatch")

# Map geometry: 8x8 grid of 100x100 cells covering an 800x800 coordinate system.
MAP_SIZE = 800
GRID_SIZE = 8
CELL_SIZE = 100
COORD_MIN = 0
COORD_MAX = MAP_SIZE

# Economic and rider defaults.
INITIAL_FUNDS = 1000
RECRUIT_COST = 300
RECRUIT_THRESHOLD = 300
RIDER_START_X = 435
RIDER_START_Y = 385
RIDER_SPEED = 10

DEFAULT_STATE_FILE = "dispatch_state.json"
DEFAULT_LOG_FILE = "dispatch.log"

DEFAULT_SETTINGS: Dict[str, Any] = {
    "initial_funds": INITIAL_FUNDS,
    "recruit_cost": RECRUIT_COST,
    "recruit_threshold": RECRUIT_THRESHOLD,
    "rider_start_x": RIDER_START_X,
    "rider_start_y": RIDER_START_Y,
    "rider_speed": RIDER_SPEED,
    "state_file": DEFAULT_STATE_FILE,
}


def load_config(path: Optional[str] = None) -> Dict[str, Any]:
    """Load system parameters from a JSON file, falling back to defaults.

    Unknown keys, wrong types and out-of-range values are ignored with a
    warning so that a damaged configuration never prevents startup.

    Args:
        path: Path to the JSON configuration file. ``None`` uses defaults.

    Returns:
        A new dictionary containing every key from ``DEFAULT_SETTINGS``.
    """
    settings = dict(DEFAULT_SETTINGS)
    if not path:
        return settings
    if not os.path.exists(path):
        LOGGER.warning("Config file %s not found; using defaults.", path)
        return settings
    try:
        with open(path, "r", encoding="utf-8") as handle:
            data = json.load(handle)
    except (OSError, ValueError) as exc:
        LOGGER.warning("Could not read config %s (%s); using defaults.", path, exc)
        return settings
    if not isinstance(data, dict):
        LOGGER.warning("Config %s must contain a JSON object; using defaults.", path)
        return settings

    for key, value in data.items():
        if key not in settings:
            LOGGER.warning("Unknown config key '%s' ignored.", key)
            continue
        expected = type(settings[key])
        if expected is int and isinstance(value, bool):
            LOGGER.warning("Config key '%s' must be an integer.", key)
            continue
        if not isinstance(value, expected):
            LOGGER.warning("Config key '%s' has wrong type; ignored.", key)
            continue
        if key == "rider_speed" and value <= 0:
            LOGGER.warning("rider_speed must be positive; ignored.")
            continue
        if key in ("rider_start_x", "rider_start_y") and not (
            COORD_MIN <= value <= COORD_MAX
        ):
            LOGGER.warning("%s must be within 0-%d; ignored.", key, COORD_MAX)
            continue
        if key in ("initial_funds", "recruit_cost", "recruit_threshold") and value < 0:
            LOGGER.warning("%s must not be negative; ignored.", key)
            continue
        settings[key] = value
    return settings


def save_state(path: str, data: Dict[str, Any]) -> None:
    """Write a JSON snapshot of the system state atomically.

    Args:
        path: Destination file path.
        data: JSON-serialisable dictionary produced by ``SystemManager.to_dict``.

    Raises:
        OSError: If the file cannot be written.
    """
    temp_path = path + ".tmp"
    with open(temp_path, "w", encoding="utf-8") as handle:
        json.dump(data, handle, indent=2)
    os.replace(temp_path, path)
