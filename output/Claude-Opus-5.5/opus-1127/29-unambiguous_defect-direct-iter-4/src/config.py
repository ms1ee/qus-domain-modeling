"""Configuration loading for the dispatch simulator."""

import json
import logging
import os

logger = logging.getLogger(__name__)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DEFAULT_CONFIG_PATH = os.path.join(BASE_DIR, "config.json")

MAP_SIZE = 800
CELL_SIZE = 100
GRID_SIZE = 8

DEFAULT_CONFIG = {
    "initial_funds": 10000,
    "rider_cost": 1000,
    "rider_speed": 50,
    "max_riders": 10,
    "order_revenue": 15,
    "state_file": "dispatch_state.json",
    "max_log_entries": 1000,
}


def load_config(path=None):
    """Load configuration from a JSON file merged over the defaults.

    Invalid or missing files are tolerated: defaults are used instead.
    """
    cfg = dict(DEFAULT_CONFIG)
    path = path or DEFAULT_CONFIG_PATH
    if path and os.path.exists(path):
        try:
            with open(path, "r", encoding="utf-8") as fh:
                data = json.load(fh)
            if isinstance(data, dict):
                for key, default in DEFAULT_CONFIG.items():
                    if key in data:
                        value = data[key]
                        if isinstance(default, int) and not isinstance(value, bool):
                            try:
                                value = int(value)
                            except (TypeError, ValueError):
                                logger.warning("Invalid config value for %s", key)
                                continue
                        cfg[key] = value
        except (OSError, ValueError) as exc:
            logger.warning("Failed to load config %s: %s", path, exc)
    if cfg["rider_speed"] < 1:
        cfg["rider_speed"] = DEFAULT_CONFIG["rider_speed"]
    if cfg["max_riders"] < 1:
        cfg["max_riders"] = DEFAULT_CONFIG["max_riders"]
    return cfg
