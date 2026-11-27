"""Configuration handling (JSON based)."""

import json
import logging
import os

logger = logging.getLogger(__name__)


class Configuration:
    """System parameters, optionally loaded from / saved to a JSON file."""

    DEFAULTS = {
        "initial_funds": 500,
        "rider_recruit_cost": 300,
        "recruit_threshold": 300,
        "order_income": 100,
        "delivery_bonus": 0,
        "default_speed": 50,
        "max_riders": 50,
        "spawn_x": 400,
        "spawn_y": 400,
        "data_file": "dispatch_data.json",
    }

    def __init__(self, file_path=None, **overrides):
        self.__dict__["values"] = dict(self.DEFAULTS)
        self.__dict__["file_path"] = file_path
        if file_path and os.path.exists(file_path):
            self.load(file_path)
        self.values.update(overrides)

    def __getattr__(self, name):
        values = self.__dict__.get("values", {})
        if name in values:
            return values[name]
        raise AttributeError(name)

    def __setattr__(self, name, value):
        if name in ("file_path",):
            self.__dict__[name] = value
        else:
            self.values[name] = value

    def get(self, key, default=None):
        """Return a configuration value."""
        return self.values.get(key, default)

    def load(self, file_path=None):
        """Load values from a JSON file; invalid files are ignored with a warning."""
        path = file_path or self.file_path
        try:
            with open(path, "r", encoding="utf-8") as fh:
                data = json.load(fh)
            if isinstance(data, dict):
                for key, value in data.items():
                    if key in self.DEFAULTS and isinstance(
                            value, type(self.DEFAULTS[key])):
                        self.values[key] = value
            return True
        except (OSError, ValueError) as exc:
            logger.warning("Could not load configuration %s: %s", path, exc)
            return False

    def save(self, file_path=None):
        """Save values to a JSON file."""
        path = file_path or self.file_path or "config.json"
        with open(path, "w", encoding="utf-8") as fh:
            json.dump(self.values, fh, indent=2)
        return path

    def to_dict(self):
        """Return a copy of the configuration values."""
        return dict(self.values)
