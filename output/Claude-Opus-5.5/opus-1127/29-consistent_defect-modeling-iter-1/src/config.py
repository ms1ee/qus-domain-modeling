"""Configuration loading and JSON persistence."""

import json
import logging
import os

logger = logging.getLogger(__name__)

DEFAULT_CONFIG = {
    "initial_funds": 1000,
    "rider_speed": 20,
    "recruitment_cost": 500,
    "recruitment_threshold": 300,
    "state_file": "dispatch_state.json",
}


class Configuration:
    """System parameters, optionally loaded from a JSON file."""

    def __init__(self, file_path="config.json"):
        self.file_path = file_path
        self.values = dict(DEFAULT_CONFIG)

    @property
    def initial_funds(self):
        """Initial system funds."""
        return self.values["initial_funds"]

    @property
    def rider_speed(self):
        """Rider speed in units per tick."""
        return self.values["rider_speed"]

    def load(self):
        """Load configuration from ``file_path`` if it exists.

        Invalid files are ignored (defaults are kept).
        """
        if not self.file_path or not os.path.exists(self.file_path):
            return self.values
        try:
            with open(self.file_path, "r", encoding="utf-8") as handle:
                data = json.load(handle)
            if isinstance(data, dict):
                for key, value in data.items():
                    if key in DEFAULT_CONFIG and isinstance(
                            value, type(DEFAULT_CONFIG[key])):
                        self.values[key] = value
        except (OSError, ValueError) as exc:
            logger.warning("Could not load config %s: %s", self.file_path, exc)
        return self.values

    def save(self):
        """Write current configuration to ``file_path``."""
        try:
            with open(self.file_path, "w", encoding="utf-8") as handle:
                json.dump(self.values, handle, indent=2)
            return True
        except OSError as exc:
            logger.warning("Could not save config: %s", exc)
            return False


def save_state(path, data):
    """Persist ``data`` (a JSON-serialisable dict) to ``path``."""
    try:
        with open(path, "w", encoding="utf-8") as handle:
            json.dump(data, handle, indent=2)
        return True
    except (OSError, TypeError, ValueError) as exc:
        logger.warning("Could not save state: %s", exc)
        return False
