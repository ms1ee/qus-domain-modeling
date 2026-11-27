"""Configuration handling (JSON based) for the dispatch simulator."""

import json
import logging
import os

logger = logging.getLogger(__name__)

DEFAULT_CONFIG_PATH = "dispatch_config.json"


class Configuration:
    """System parameters, optionally loaded from a JSON file."""

    def __init__(self, file_path=None, initial_funds=1000, recruitment_cost=300,
                 initial_rider_x=435, initial_rider_y=385, default_speed=10):
        self.file_path = file_path
        self.initial_funds = initial_funds
        self.recruitment_cost = recruitment_cost
        self.initial_rider_x = initial_rider_x
        self.initial_rider_y = initial_rider_y
        self.default_speed = default_speed

    def to_dict(self):
        """Return the configuration as a plain dictionary."""
        return {
            "initial_funds": self.initial_funds,
            "recruitment_cost": self.recruitment_cost,
            "initial_rider_x": self.initial_rider_x,
            "initial_rider_y": self.initial_rider_y,
            "default_speed": self.default_speed,
        }

    @classmethod
    def from_dict(cls, data, file_path=None):
        """Build a configuration from a dictionary, ignoring unknown keys."""
        cfg = cls(file_path=file_path)
        for key in cfg.to_dict():
            if key in data:
                try:
                    setattr(cfg, key, int(data[key]))
                except (TypeError, ValueError):
                    logger.warning("Invalid config value for %s: %r", key, data[key])
        return cfg

    @classmethod
    def load(cls, file_path=None):
        """Load configuration from ``file_path``; fall back to defaults."""
        if not file_path or not os.path.exists(file_path):
            return cls(file_path=file_path)
        try:
            with open(file_path, "r", encoding="utf-8") as fh:
                data = json.load(fh)
            if isinstance(data, dict) and isinstance(data.get("config"), dict):
                data = data["config"]
            return cls.from_dict(data if isinstance(data, dict) else {}, file_path)
        except (OSError, ValueError) as exc:
            logger.warning("Could not load config %s: %s", file_path, exc)
            return cls(file_path=file_path)

    def save(self, file_path=None):
        """Write the configuration to a JSON file."""
        path = file_path or self.file_path or DEFAULT_CONFIG_PATH
        with open(path, "w", encoding="utf-8") as fh:
            json.dump(self.to_dict(), fh, indent=2)
        return path
