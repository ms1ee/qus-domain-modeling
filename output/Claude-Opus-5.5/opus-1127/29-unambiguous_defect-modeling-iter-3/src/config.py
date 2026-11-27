"""Configuration handling (system parameters with optional JSON override)."""

import json
import logging
import os

logger = logging.getLogger(__name__)

DEFAULTS = {
    "initial_funds": 1000,
    "recruitment_cost": 100,
    "default_speed": 50,
    "max_riders": 10,
    "rider_start_x": 400,
    "rider_start_y": 400,
    "delivery_fee": 0,
    "state_file": "dispatch_state.json",
}

DEFAULT_CONFIG_FILE = "config.json"


class Configuration:
    """System parameters, optionally loaded from a JSON file."""

    def __init__(self, file_path=None):
        self.file_path = file_path or DEFAULT_CONFIG_FILE
        self.values = dict(DEFAULTS)
        self.load()

    # Convenience attributes mirroring the domain model
    @property
    def initial_funds(self):
        return int(self.values["initial_funds"])

    @property
    def recruitment_cost(self):
        return int(self.values["recruitment_cost"])

    @property
    def default_speed(self):
        return int(self.values["default_speed"])

    def load(self):
        """Load overrides from the JSON file if it exists; ignore bad files."""
        if not self.file_path or not os.path.isfile(self.file_path):
            return False
        try:
            with open(self.file_path, "r", encoding="utf-8") as fh:
                data = json.load(fh)
        except (OSError, ValueError) as exc:
            logger.warning("Could not read config %s: %s", self.file_path, exc)
            return False
        if not isinstance(data, dict):
            logger.warning("Config file %s is not a JSON object", self.file_path)
            return False
        params = data.get("system", data)
        for key, default in DEFAULTS.items():
            if key in params:
                try:
                    if isinstance(default, int):
                        self.values[key] = int(params[key])
                    else:
                        self.values[key] = str(params[key])
                except (TypeError, ValueError):
                    logger.warning("Invalid value for %s in config", key)
        if self.values["default_speed"] <= 0:
            self.values["default_speed"] = DEFAULTS["default_speed"]
        return True

    def as_dict(self):
        """Return a copy of the configuration values."""
        return dict(self.values)
