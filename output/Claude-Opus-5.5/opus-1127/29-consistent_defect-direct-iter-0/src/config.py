"""System-wide constants and configuration loading."""

import json
import logging
import os

logger = logging.getLogger(__name__)

MAP_SIZE = 800
CELL_SIZE = 100
GRID_DIM = MAP_SIZE // CELL_SIZE  # 8

INITIAL_FUNDS = 1000
RIDER_COST = 500
RECRUIT_THRESHOLD = 300
RIDER_SPEED = 20
RIDER_START = (400, 400)

INPUT_MIN = 0
INPUT_MAX = 1000

MAP_CHARS = 16  # ASCII map is 16x16
DEFAULT_SAVE_FILE = "dispatch_state.json"
DEFAULT_CONFIG_FILE = "config.json"

DEFAULTS = {
    "initial_funds": INITIAL_FUNDS,
    "rider_cost": RIDER_COST,
    "recruit_threshold": RECRUIT_THRESHOLD,
    "rider_speed": RIDER_SPEED,
    "rider_start": list(RIDER_START),
}


def load_config(path=DEFAULT_CONFIG_FILE):
    """Load a JSON configuration file, falling back to defaults.

    Unknown keys are ignored; invalid files produce a warning and defaults.
    """
    cfg = dict(DEFAULTS)
    if not path or not os.path.exists(path):
        return cfg
    try:
        with open(path, "r", encoding="utf-8") as fh:
            data = json.load(fh)
        if isinstance(data, dict):
            for key in DEFAULTS:
                if key in data:
                    cfg[key] = data[key]
    except (OSError, ValueError) as exc:
        logger.warning("Could not load config %s: %s", path, exc)
    return cfg
