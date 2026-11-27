"""Configuration handling (JSON based)."""

import json
import logging
import os

logger = logging.getLogger(__name__)

DEFAULTS = {
    "initial_funds": 300,
    "recruitment_threshold": 300,
    "recruitment_cost": 300,
    "order_revenue": 100,
    "rider_speed": 20,
    "max_riders": 20,
    "spawn_x": 0,
    "spawn_y": 0,
    "state_file": "dispatch_state.json",
}


class Configuration:
    """System parameters, optionally loaded from a JSON file."""

    def __init__(self, file_path=None):
        self.file_path = file_path
        self.params = dict(DEFAULTS)
        if file_path and os.path.exists(file_path):
            self.load(file_path)

    def load(self, file_path):
        """Merge parameters from a JSON file into the defaults."""
        try:
            with open(file_path, "r", encoding="utf-8") as fh:
                data = json.load(fh)
            if isinstance(data, dict):
                for key, value in data.items():
                    if key in DEFAULTS:
                        self.params[key] = value
        except (OSError, ValueError) as exc:
            logger.warning("Could not load configuration %s: %s", file_path, exc)

    def save(self, file_path=None):
        """Write the current parameters to a JSON file."""
        path = file_path or self.file_path
        if not path:
            return False
        try:
            with open(path, "w", encoding="utf-8") as fh:
                json.dump(self.params, fh, indent=2)
            return True
        except OSError as exc:
            logger.warning("Could not save configuration: %s", exc)
            return False

    def get(self, key, default=None):
        """Return a configuration value."""
        return self.params.get(key, DEFAULTS.get(key, default))

    @property
    def recruitment_threshold(self):
        """Funds threshold that triggers automatic rider recruitment."""
        return int(self.get("recruitment_threshold"))
