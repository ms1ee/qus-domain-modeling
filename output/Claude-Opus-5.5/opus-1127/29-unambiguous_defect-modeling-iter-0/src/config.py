"""JSON configuration and state persistence."""

import json
import logging
import os

import globalvar
from order_model import Order
from rider import Rider
from system import DEFAULT_CONFIG

logger = logging.getLogger(__name__)


class Configuration:
    """System parameters loaded from / saved to a JSON file."""

    def __init__(self, file_path="config.json"):
        self.file_path = file_path
        self.values = dict(DEFAULT_CONFIG)

    @property
    def initial_funds(self):
        return self.values["initial_funds"]

    @property
    def recruitment_cost(self):
        return self.values["recruitment_cost"]

    def load(self):
        """Load parameters if the file exists. Returns the values dict."""
        if self.file_path and os.path.exists(self.file_path):
            try:
                with open(self.file_path, "r", encoding="utf-8") as fh:
                    data = json.load(fh)
                params = data.get("system", data) if isinstance(data, dict) else {}
                for key in DEFAULT_CONFIG:
                    if key in params:
                        self.values[key] = int(params[key])
            except (OSError, ValueError, TypeError) as exc:
                logger.warning("Could not read config %s: %s", self.file_path, exc)
        return dict(self.values)

    def save(self):
        """Write parameters to the file."""
        with open(self.file_path, "w", encoding="utf-8") as fh:
            json.dump({"system": self.values}, fh, indent=2)

    def to_dict(self):
        return dict(self.values)


def save_state(path):
    """Save system parameters, riders and order history to JSON."""
    keys = ("funds", "rider_id_counter", "tick", "order_id_counter",
            "recruitment_cost", "max_riders", "rider_speed", "ticks_per_command")
    data = {
        "system": {k: globalvar.get_value(k) for k in keys},
        "riders": [r.to_dict() for r in (globalvar.get_value("riders", []) or [])],
        "orders": [o.to_dict() for o in (globalvar.get_value("orders", []) or [])],
    }
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(data, fh, indent=2)


def load_state(path):
    """Restore state saved by :func:`save_state`."""
    with open(path, "r", encoding="utf-8") as fh:
        data = json.load(fh)
    orders = [Order.from_dict(d) for d in data.get("orders", [])]
    by_id = {o.id: o for o in orders}
    riders = [Rider.from_dict(d, by_id) for d in data.get("riders", [])]
    for key, value in data.get("system", {}).items():
        if value is not None:
            globalvar.set_value(key, value)
    globalvar.set_value("orders", orders)
    globalvar.set_value("riders", riders)
    globalvar.set_value("running", True)
