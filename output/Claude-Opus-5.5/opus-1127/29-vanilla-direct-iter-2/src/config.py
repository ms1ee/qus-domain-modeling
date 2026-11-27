"""Configuration loading and JSON persistence of system state."""

import json
import logging
import os

import globalvar

logger = logging.getLogger(__name__)

DEFAULT_CONFIG = {
    "initial_funds": 1000,
    "recruit_cost": 300,
    "rider_speed": 10,
    "rider_spawn": [435, 385],
    "map_size": 800,
    "cell_size": 100,
    "delivery_income": 0,
}


def load_config(path=None):
    """Load configuration from a JSON file, merged over the defaults.

    Missing or malformed files fall back to the defaults.
    """
    cfg = dict(DEFAULT_CONFIG)
    if path and os.path.exists(path):
        try:
            with open(path, "r", encoding="utf-8") as fh:
                data = json.load(fh)
            if isinstance(data, dict):
                for key in DEFAULT_CONFIG:
                    if key in data:
                        cfg[key] = data[key]
        except (OSError, ValueError) as exc:
            logger.warning("Could not read config %s: %s", path, exc)
    return cfg


def write_default_config(path):
    """Write the default configuration file to ``path``."""
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(DEFAULT_CONFIG, fh, indent=2)


def build_state():
    """Return a JSON-serialisable snapshot of the system state."""
    riders = globalvar.get_value("riders", []) or []
    orders = globalvar.get_value("orders", []) or []
    return {
        "config": globalvar.get_value("config", DEFAULT_CONFIG),
        "system": {
            "funds": globalvar.get_value("funds"),
            "time": globalvar.get_value("time"),
            "rider_id_counter": globalvar.get_value("rider_id_counter"),
        },
        "riders": [r.to_dict() for r in riders],
        "orders": [o.to_dict() for o in orders],
    }


def save_state(path="dispatch_state.json"):
    """Persist the current system state as JSON. Returns the path."""
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(build_state(), fh, indent=2)
    return path
