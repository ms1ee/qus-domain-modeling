"""JSON configuration and data persistence."""

import json
import logging
import os

logger = logging.getLogger("dispatch.config")

DEFAULTS = {
    "initial_funds": 1000,
    "recruitment_threshold": 300,
    "rider_cost": 300,
    "rider_speed": 50,
    "rider_start": [400, 400],
    "max_riders": 20,
    "base_fee": 30,
    "fee_per_100_units": 10,
    "max_order_history": 10000,
    "max_log_entries": 5000,
    "data_file": "dispatch_data.json",
}


class Configuration:
    """System parameters, optionally loaded from a JSON file."""

    def __init__(self, file_path=None):
        self.file_path = file_path
        self.parameters = dict(DEFAULTS)
        if file_path and os.path.exists(file_path):
            self.load()

    def load(self):
        """Load parameters from ``file_path``; invalid files are ignored."""
        try:
            with open(self.file_path, "r", encoding="utf-8") as fh:
                data = json.load(fh)
            params = data.get("parameters", data) if isinstance(data, dict) else {}
            for key, value in params.items():
                if key in DEFAULTS:
                    self.parameters[key] = value
        except (OSError, ValueError) as exc:
            logger.warning("Could not load config %s: %s", self.file_path, exc)

    def save(self, path=None):
        """Save parameters to JSON."""
        path = path or self.file_path
        if not path:
            return False
        with open(path, "w", encoding="utf-8") as fh:
            json.dump({"parameters": self.parameters}, fh, indent=2)
        return True

    def get(self, key, default=None):
        return self.parameters.get(key, DEFAULTS.get(key, default))

    @staticmethod
    def save_data(path, data):
        """Persist a data snapshot (system, riders, orders) as JSON."""
        with open(path, "w", encoding="utf-8") as fh:
            json.dump(data, fh, indent=2)
        return True
