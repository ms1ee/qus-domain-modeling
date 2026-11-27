"""Configuration loading and state persistence (JSON)."""

import json
import logging
import os

import globalvar

logger = logging.getLogger(__name__)

DEFAULT_CONFIG_PATH = "config.json"

DEFAULT_CONFIG = {
    "initial_funds": 10000,
    "recruitment_cost": 1000,
    "default_speed": 50,
    "max_riders": 20,
    "start_x": 400,
    "start_y": 400,
    "state_file": "dispatch_state.json",
}


class Configuration:
    """Holds the configuration values together with their source path."""

    def __init__(self, file_path=None, values=None):
        self.file_path = file_path
        self.values = dict(DEFAULT_CONFIG)
        if values:
            self.values.update(values)

    def __getitem__(self, key):
        return self.values[key]

    def get(self, key, default=None):
        """Return a configuration value."""
        return self.values.get(key, default)

    @property
    def initial_funds(self):
        return int(self.values["initial_funds"])

    @property
    def recruitment_cost(self):
        return int(self.values["recruitment_cost"])

    @property
    def default_speed(self):
        return int(self.values["default_speed"])


def load_config(path=None):
    """Load configuration from ``path``, falling back to defaults.

    Unknown keys are ignored, invalid values fall back to the defaults.
    """
    cfg = dict(DEFAULT_CONFIG)
    if path and os.path.exists(path):
        try:
            with open(path, "r", encoding="utf-8") as fh:
                data = json.load(fh)
            if isinstance(data, dict):
                for key, default in DEFAULT_CONFIG.items():
                    if key in data:
                        try:
                            cfg[key] = type(default)(data[key])
                        except (TypeError, ValueError):
                            logger.warning("Invalid config value for %s", key)
        except (OSError, ValueError) as exc:
            logger.warning("Could not read config %s: %s", path, exc)
    if cfg["default_speed"] <= 0:
        cfg["default_speed"] = DEFAULT_CONFIG["default_speed"]
    return cfg


def save_config(cfg, path):
    """Write a configuration dictionary to ``path``."""
    try:
        with open(path, "w", encoding="utf-8") as fh:
            json.dump(cfg, fh, indent=2)
        return True
    except OSError as exc:
        logger.warning("Could not write config %s: %s", path, exc)
        return False


def build_state():
    """Build a JSON-serialisable snapshot of the system."""
    riders = globalvar.get_value("riders", []) or []
    orders = globalvar.get_value("orders", []) or []
    return {
        "config": globalvar.get_value("config", {}),
        "system": {
            "funds": globalvar.get_value("funds", 0),
            "tick": globalvar.get_value("tick", 0),
            "rider_id_counter": globalvar.get_value("rider_id_counter", 0),
        },
        "riders": [r.to_dict() for r in riders],
        "orders": [o.to_dict() for o in orders],
    }


def save_state(path):
    """Persist system parameters, riders and order history to ``path``."""
    try:
        with open(path, "w", encoding="utf-8") as fh:
            json.dump(build_state(), fh, indent=2)
        return True
    except (OSError, TypeError, ValueError) as exc:
        logger.warning("Could not save state to %s: %s", path, exc)
        return False
