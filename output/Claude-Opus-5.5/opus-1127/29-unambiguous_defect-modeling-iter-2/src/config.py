"""Configuration defaults and loading for the dispatch simulator."""

import json
import logging
import os

logger = logging.getLogger(__name__)

DEFAULT_CONFIG = {
    "initial_funds": 10000,
    "recruitment_cost": 1000,
    "rider_speed": 100,
    "max_riders": 10,
    "map_size": 800,
    "cell_size": 100,
    "state_file": "dispatch_state.json",
}


def load_config(path=None):
    """Load configuration from a JSON file merged over the defaults.

    Unknown keys are ignored; invalid files fall back to defaults.

    :param path: path of a JSON configuration file, or None.
    :return: configuration dictionary.
    """
    cfg = dict(DEFAULT_CONFIG)
    if not path or not os.path.exists(path):
        return cfg
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
        logger.warning("Could not load config %s: %s", path, exc)
    return cfg
