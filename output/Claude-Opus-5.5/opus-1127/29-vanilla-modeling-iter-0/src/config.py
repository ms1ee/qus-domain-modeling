"""Configuration handling (JSON based) for the dispatch system."""

import json
import logging
import os

logger = logging.getLogger(__name__)

DEFAULT_CONFIG = {
    "initial_funds": 1000,
    "recruitment_cost": 300,
    "rider_speed": 10,
    "initial_rider_x": 435,
    "initial_rider_y": 385,
    "map_size": 800,
    "cell_size": 100,
    "state_file": "dispatch_state.json",
    "autosave": False,
}


def load_config(path=None):
    """Load configuration from a JSON file, merged over the defaults.

    Missing files or invalid content fall back to the defaults.
    """
    cfg = dict(DEFAULT_CONFIG)
    if path and os.path.isfile(path):
        try:
            with open(path, "r", encoding="utf-8") as fh:
                data = json.load(fh)
            if isinstance(data, dict):
                for key, value in data.items():
                    if key in cfg:
                        cfg[key] = value
        except (OSError, ValueError) as exc:
            logger.warning("Could not load config %s: %s", path, exc)
    return cfg


def save_config(cfg, path):
    """Write the configuration dictionary to ``path`` as JSON."""
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(cfg, fh, indent=2)
