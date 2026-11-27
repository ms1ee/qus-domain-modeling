"""Configuration handling (JSON file based)."""

import json
import logging
import os

logger = logging.getLogger(__name__)

DEFAULT_CONFIG_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                   "config.json")

DEFAULTS = {
    "initial_funds": 300,
    "recruit_threshold": 300,
    "recruit_cost": 300,
    "max_riders": 50,
    "rider_speed": 50,
    "rider_start_x": 400,
    "rider_start_y": 400,
    "base_fee": 20,
    "fee_per_100": 5,
    "map_size": 800,
    "cell_size": 100,
    "max_log_entries": 5000,
    "max_history": 500,
    "state_file": "dispatch_state.json",
    "autosave_on_exit": True,
}


class Configuration:
    """System parameters loaded from a JSON configuration file."""

    def __init__(self, file_path=None):
        self.file_path = file_path or DEFAULT_CONFIG_PATH
        self.values = dict(DEFAULTS)
        self.load()

    @property
    def recruit_threshold(self):
        """Funds threshold for automatic rider recruitment."""
        return int(self.values.get("recruit_threshold", 300))

    def load(self):
        """Load the configuration file, silently falling back to defaults."""
        if not self.file_path or not os.path.exists(self.file_path):
            return
        try:
            with open(self.file_path, "r", encoding="utf-8") as fh:
                data = json.load(fh)
            if isinstance(data, dict):
                for key, value in data.items():
                    if key in DEFAULTS and value is not None:
                        self.values[key] = value
        except (OSError, ValueError) as exc:
            logger.warning("Could not read config %s: %s", self.file_path, exc)

    def save(self, path=None):
        """Write the configuration to disk."""
        target = path or self.file_path
        with open(target, "w", encoding="utf-8") as fh:
            json.dump(self.values, fh, indent=4)

    def get(self, key, default=None):
        """Return a configuration value."""
        return self.values.get(key, DEFAULTS.get(key, default))

    def set(self, key, value):
        """Set a configuration value."""
        self.values[key] = value

    def to_dict(self):
        """Return a copy of all configuration values."""
        return dict(self.values)
