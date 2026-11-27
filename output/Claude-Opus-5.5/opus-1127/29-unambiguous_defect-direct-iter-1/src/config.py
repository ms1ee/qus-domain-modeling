"""Default configuration values and configuration file helpers."""

import json
import logging
import os

logger = logging.getLogger(__name__)

MAP_SIZE = 800
CELL_SIZE = 100
GRID_DIM = MAP_SIZE // CELL_SIZE

DEFAULT_CONFIG = {
    "initial_funds": 10000,
    "rider_cost": 1000,
    "rider_speed": 100,
    "max_riders": 20,
    "delivery_fee": 50,
    "state_file": "dispatch_state.json",
}


def load_config(path="config.json"):
    """Load a JSON configuration file and merge it with the defaults.

    Missing or malformed files silently fall back to the defaults.
    """
    cfg = dict(DEFAULT_CONFIG)
    if path and os.path.isfile(path):
        try:
            with open(path, "r", encoding="utf-8") as fh:
                data = json.load(fh)
            if isinstance(data, dict):
                for key, value in data.items():
                    if key in DEFAULT_CONFIG:
                        cfg[key] = value
        except (OSError, ValueError) as exc:
            logger.warning("Could not read config file %s: %s", path, exc)
    return cfg
