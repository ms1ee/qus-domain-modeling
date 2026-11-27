"""System parameter configuration (JSON based)."""

import json
import logging
import os

logger = logging.getLogger("dispatch.config")

DEFAULT_CONFIG_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                   "dispatch_config.json")

DEFAULT_CONFIG = {
    "initial_funds": 10000,
    "rider_cost": 1000,
    "rider_speed": 50,
    "rider_start_x": 400,
    "rider_start_y": 400,
    "max_riders": 20,
    "map_size": 800,
    "cell_size": 100,
}


def load_config(path=None):
    """Load configuration from a JSON file merged over the defaults.

    If ``path`` is None the default file next to this module is used if it
    exists.  Invalid files are ignored (defaults are used instead).
    """
    cfg = dict(DEFAULT_CONFIG)
    if path is None:
        path = DEFAULT_CONFIG_FILE
    if path and os.path.isfile(path):
        try:
            with open(path, "r", encoding="utf-8") as fh:
                data = json.load(fh)
            if isinstance(data, dict):
                params = data.get("system", data)
                for key in DEFAULT_CONFIG:
                    if key in params and isinstance(params[key], int):
                        cfg[key] = params[key]
        except (OSError, ValueError) as exc:
            logger.warning("Could not read config %s: %s", path, exc)
    return cfg


def get_config_value(key):
    """Return a configuration value from the active config or defaults."""
    import globalvar
    cfg = globalvar.get_value("config")
    if isinstance(cfg, dict) and key in cfg:
        return cfg[key]
    return DEFAULT_CONFIG[key]
