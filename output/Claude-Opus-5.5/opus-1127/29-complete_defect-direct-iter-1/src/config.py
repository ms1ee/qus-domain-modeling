"""Configuration handling (JSON based) for the dispatch system."""

import json
import logging
import os

logger = logging.getLogger(__name__)

DEFAULT_CONFIG_FILE = "config.json"

DEFAULTS = {
    "initial_funds": 300,
    "rider_cost": 300,
    "recruit_threshold": 300,
    "rider_speed": 100,
    "spawn_x": 400,
    "spawn_y": 400,
    "base_fee": 30,
    "fee_per_100": 5,
    "map_size": 800,
    "cell_size": 100,
    "state_file": "dispatch_state.json",
}


def load_config(path=DEFAULT_CONFIG_FILE):
    """Load configuration from a JSON file, merged over the defaults.

    Missing or invalid files are ignored and the defaults are used.
    """
    cfg = dict(DEFAULTS)
    if path and os.path.isfile(path):
        try:
            with open(path, "r", encoding="utf-8") as fh:
                data = json.load(fh)
            if isinstance(data, dict):
                for key, value in data.items():
                    if key in DEFAULTS and isinstance(value, type(DEFAULTS[key])):
                        cfg[key] = value
        except (OSError, ValueError) as exc:
            logger.warning("Could not load config file %s: %s", path, exc)
    return cfg


def get_config():
    """Return the active configuration (from globals, or defaults)."""
    import globalvar
    cfg = globalvar.get_value("config")
    if not isinstance(cfg, dict):
        return dict(DEFAULTS)
    return cfg
