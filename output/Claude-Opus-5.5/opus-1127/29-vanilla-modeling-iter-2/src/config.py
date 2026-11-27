"""Configuration loading for the dispatch simulator."""

import json
import logging
import os

logger = logging.getLogger(__name__)

DEFAULT_CONFIG = {
    "initial_funds": 1000,
    "recruitment_cost": 300,
    "rider_speed": 10,
    "rider_start": [435, 385],
}


def load_config(path=None):
    """Load configuration from a JSON file, merged over the defaults.

    Missing or invalid files fall back to defaults.
    """
    cfg = dict(DEFAULT_CONFIG)
    if not path:
        return cfg
    if not os.path.exists(path):
        logger.warning("Config file %s not found, using defaults", path)
        return cfg
    try:
        with open(path, "r", encoding="utf-8") as fh:
            data = json.load(fh)
        if isinstance(data, dict):
            for key in DEFAULT_CONFIG:
                if key in data:
                    cfg[key] = data[key]
    except (OSError, ValueError) as exc:
        logger.error("Failed to read config %s: %s", path, exc)
    return cfg
