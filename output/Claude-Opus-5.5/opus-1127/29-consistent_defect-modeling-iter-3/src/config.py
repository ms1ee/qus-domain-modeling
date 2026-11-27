"""Configuration handling (JSON based)."""

import json
import logging
import os

logger = logging.getLogger(__name__)

DEFAULTS = {
    "initial_funds": 1000,
    "recruitment_cost": 500,
    "recruit_threshold": 300,
    "rider_speed": 20,
    "rider_start_x": 400,
    "rider_start_y": 400,
    "map_size": 800,
    "cell_size": 100,
    "state_file": "dispatch_state.json",
}


class Configuration:
    """System parameters, optionally loaded from a JSON file."""

    def __init__(self, file_path=None):
        self.file_path = file_path
        self.values = dict(DEFAULTS)
        if file_path:
            self.load(file_path)

    def load(self, file_path):
        """Load parameters from a JSON file; unknown/invalid entries are ignored."""
        if not file_path or not os.path.exists(file_path):
            return False
        try:
            with open(file_path, "r", encoding="utf-8") as fh:
                data = json.load(fh)
            params = data.get("system", data) if isinstance(data, dict) else {}
            for key in DEFAULTS:
                if key in params and isinstance(params[key], type(DEFAULTS[key])):
                    self.values[key] = params[key]
            return True
        except (OSError, ValueError) as exc:
            logger.warning("Could not load configuration %s: %s", file_path, exc)
            return False

    def save(self, file_path=None):
        """Save parameters to a JSON file."""
        path = file_path or self.file_path or "config.json"
        with open(path, "w", encoding="utf-8") as fh:
            json.dump({"system": self.values}, fh, indent=2)
        return path

    def get(self, key):
        """Return a configuration value."""
        return self.values.get(key, DEFAULTS.get(key))

    @property
    def initial_funds(self):
        return self.get("initial_funds")

    @property
    def recruitment_cost(self):
        return self.get("recruitment_cost")

    @property
    def rider_speed(self):
        return self.get("rider_speed")
