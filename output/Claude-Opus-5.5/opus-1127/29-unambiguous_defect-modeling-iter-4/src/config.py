"""Configuration handling (JSON based) for the dispatch system."""

import json
import logging
import os

logger = logging.getLogger(__name__)

DEFAULT_CONFIG = {
    "initial_funds": 10000,
    "recruitment_cost": 1000,
    "max_riders": 20,
    "rider_speed": 50,
    "rider_spawn": [400, 400],
    "order_revenue": 0,
    "state_file": "dispatch_state.json",
    "autosave": True,
}


class Configuration:
    """Loads system parameters from a JSON file, falling back to defaults.

    Attributes:
        file_path: Path of the configuration file (may be None).
        data: Dictionary of the effective configuration.
    """

    def __init__(self, file_path=None):
        self.file_path = file_path
        self.data = dict(DEFAULT_CONFIG)
        if file_path:
            self.load(file_path)

    @property
    def initial_funds(self):
        """Initial system funds."""
        return int(self.data["initial_funds"])

    @property
    def recruitment_cost(self):
        """Cost of recruiting one rider."""
        return int(self.data["recruitment_cost"])

    def load(self, file_path):
        """Load configuration values from ``file_path`` if it exists.

        Invalid files are reported and ignored (defaults remain in effect).
        """
        if not os.path.exists(file_path):
            logger.info("Config file %s not found, using defaults", file_path)
            return
        try:
            with open(file_path, "r", encoding="utf-8") as fh:
                loaded = json.load(fh)
            if not isinstance(loaded, dict):
                raise ValueError("configuration root must be an object")
            for key, value in loaded.items():
                if key in DEFAULT_CONFIG:
                    self.data[key] = value
            self._sanitize()
        except (OSError, ValueError) as exc:
            logger.warning("Could not load config %s: %s", file_path, exc)
            self.data = dict(DEFAULT_CONFIG)

    def _sanitize(self):
        """Coerce configuration values into valid types/ranges."""
        try:
            self.data["initial_funds"] = int(self.data["initial_funds"])
            self.data["recruitment_cost"] = max(0, int(self.data["recruitment_cost"]))
            self.data["max_riders"] = max(1, int(self.data["max_riders"]))
            self.data["rider_speed"] = max(1, int(self.data["rider_speed"]))
            self.data["order_revenue"] = int(self.data["order_revenue"])
            spawn = self.data["rider_spawn"]
            sx = max(0, min(800, int(spawn[0])))
            sy = max(0, min(800, int(spawn[1])))
            # riders must start on a road
            if sx % 100 != 0 and sy % 100 != 0:
                sx = (sx // 100) * 100
            self.data["rider_spawn"] = [sx, sy]
        except (TypeError, ValueError, IndexError, KeyError) as exc:
            logger.warning("Invalid configuration values (%s); using defaults", exc)
            self.data = dict(DEFAULT_CONFIG)

    def get(self, key, default=None):
        """Return the configuration value for ``key``."""
        return self.data.get(key, default)
