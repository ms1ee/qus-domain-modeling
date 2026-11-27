"""JSON configuration loading and state persistence."""

import json
import logging
import os

import globalvar

logger = logging.getLogger(__name__)

DEFAULT_CONFIG = {
    "initial_funds": 300,
    "recruitment_threshold": 300,
    "rider_cost": 300,
    "order_fee": 100,
    "rider_speed": 100,
    "spawn_x": 400,
    "spawn_y": 400,
    "map_size": 800,
    "cell_size": 100,
    "state_file": "dispatch_state.json",
    "log_level": "WARNING",
}

DEFAULT_CONFIG_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                   "config.json")


class Configuration:
    """Handles the JSON configuration file and state snapshots."""

    def __init__(self, file_path=None):
        self.file_path = file_path or DEFAULT_CONFIG_PATH
        self.format = "json"

    def load(self):
        """Load configuration parameters, falling back to defaults.

        :return: dict of parameters.
        """
        params = dict(DEFAULT_CONFIG)
        if self.file_path and os.path.exists(self.file_path):
            try:
                with open(self.file_path, "r", encoding="utf-8") as fh:
                    data = json.load(fh)
                if isinstance(data, dict):
                    for key, value in data.items():
                        if key in params and isinstance(value, type(params[key])):
                            params[key] = value
            except (OSError, ValueError) as exc:
                logger.warning("Could not read config %s: %s", self.file_path, exc)
        return params

    @staticmethod
    def build_state():
        """Build a serialisable snapshot of the simulation state."""
        riders = globalvar.get_value("riders", []) or []
        orders = globalvar.get_value("orders", []) or []
        return {
            "system": {
                "funds": globalvar.get_value("funds", 0),
                "tick": globalvar.get_value("tick", 0),
                "rider_id_counter": globalvar.get_value("rider_id_counter", 0),
                "order_id_counter": globalvar.get_value("order_id_counter", 0),
            },
            "riders": [r.to_dict() for r in riders],
            "orders": [o.to_dict() for o in orders],
        }

    def save_state(self, path=None):
        """Write the state snapshot to a JSON file.

        :return: path written, or None on failure.
        """
        path = path or globalvar.get_value("state_file", DEFAULT_CONFIG["state_file"])
        try:
            with open(path, "w", encoding="utf-8") as fh:
                json.dump(self.build_state(), fh, indent=2)
            return path
        except OSError as exc:
            logger.error("Failed to save state to %s: %s", path, exc)
            return None
