"""System initialization, configuration, and resource management."""

import json
import logging
import os
import random

import globalvar
from rider import Rider

logger = logging.getLogger("dispatch.system")

CONFIG_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), os.pardir, "config.json")

DEFAULT_CONFIG = {
    "initial_funds": 1000,
    "recruitment_cost": 200,
    "rider_speed": 50,
    "delivery_fee": 30,
    "max_orders_per_rider": 2,
}


def load_config(path=CONFIG_PATH):
    """Load system parameters from a JSON file, falling back to defaults.

    Unknown keys are ignored; non-integer or negative values are rejected.

    Args:
        path: Location of the JSON configuration file.

    Returns:
        Dictionary of configuration values.
    """
    config = dict(DEFAULT_CONFIG)
    if not os.path.isfile(path):
        return config
    try:
        with open(path, "r", encoding="utf-8") as handle:
            data = json.load(handle)
    except (OSError, json.JSONDecodeError) as exc:
        logger.warning("Could not read config %s (%s); using defaults.", path, exc)
        return config
    if not isinstance(data, dict):
        logger.warning("Config %s is not a JSON object; using defaults.", path)
        return config
    for key in DEFAULT_CONFIG:
        value = data.get(key)
        if isinstance(value, int) and not isinstance(value, bool) and value >= 0:
            config[key] = value
    if config["rider_speed"] < 1:
        config["rider_speed"] = DEFAULT_CONFIG["rider_speed"]
    if config["max_orders_per_rider"] < 1:
        config["max_orders_per_rider"] = DEFAULT_CONFIG["max_orders_per_rider"]
    return config


def init_system():
    """Initialize all global parameters for a fresh simulation.

    Sets system funds, an empty rider list, the rider id counter (0), the
    running flag (True), the simulated tick (0), and an empty order list.
    """
    globalvar._init()
    config = load_config()
    globalvar.set_value("config", config)
    globalvar.set_value("funds", int(config["initial_funds"]))
    globalvar.set_value("riders", [])
    globalvar.set_value("orders", [])
    globalvar.set_value("rider_id_counter", 0)
    globalvar.set_value("is_running", True)
    globalvar.set_value("tick", 0)
    logger.info("System initialized with funds=%s", config["initial_funds"])


class SystemManager:
    """Facade over global state: funds, riders, tick, and running flag."""

    def __init__(self):
        """Attach to the global state, initializing it if necessary."""
        if globalvar.get_value("config") is None:
            init_system()

    @property
    def funds(self):
        """Current system fund balance (may be negative)."""
        return globalvar.get_value("funds", 0)

    @funds.setter
    def funds(self, value):
        globalvar.set_value("funds", int(value))

    @property
    def rider_id_counter(self):
        """Last issued rider identifier."""
        return globalvar.get_value("rider_id_counter", 0)

    @property
    def is_running(self):
        """Whether the main loop should keep running."""
        return bool(globalvar.get_value("is_running", True))

    @is_running.setter
    def is_running(self, value):
        globalvar.set_value("is_running", bool(value))

    @property
    def current_tick(self):
        """Current simulated time in ticks."""
        return globalvar.get_value("tick", 0)

    @property
    def recruitment_cost(self):
        """Fixed cost deducted when a rider is recruited."""
        return int(self._config().get("recruitment_cost", DEFAULT_CONFIG["recruitment_cost"]))

    @property
    def riders(self):
        """The dynamic list of riders."""
        riders = globalvar.get_value("riders")
        if riders is None:
            riders = []
            globalvar.set_value("riders", riders)
        return riders

    def _config(self):
        """Return the active configuration dictionary."""
        return globalvar.get_value("config") or {}

    def can_recruit(self):
        """Return True if the system funds cover one recruitment."""
        return self.funds >= self.recruitment_cost

    def recruit_rider(self):
        """Create a new rider, deduct the recruitment cost, and register it.

        Returns:
            The newly created ``Rider``.
        """
        new_id = self.rider_id_counter + 1
        globalvar.set_value("rider_id_counter", new_id)
        self.funds = self.funds - self.recruitment_cost
        rider = Rider(new_id)
        self.riders.append(rider)
        logger.info("Recruited rider %s (funds now %s)", new_id, self.funds)
        return rider

    def remove_rider(self, rider):
        """Remove an idle rider from the roster (CRUD delete support)."""
        if rider.orders:
            raise ValueError("Cannot remove a rider who still has orders.")
        self.riders.remove(rider)

    def advance_tick(self):
        """Advance simulated time by one tick and move every rider.

        Returns:
            The new current tick value.
        """
        globalvar.set_value("tick", self.current_tick + 1)
        for rider in list(self.riders):
            try:
                rider.move()
            except Exception:  # keep the simulation alive on unexpected faults
                logger.exception("Rider %s failed to move; resetting it to idle.", rider.rider_id)
                rider.orders.clear()
                rider.state = 0
                rider.special_case = False
        return self.current_tick

    def save_state(self, path="dispatch_state.json"):
        """Persist configuration, funds, riders, and order history as JSON.

        Args:
            path: Destination file path.

        Returns:
            The path that was written.
        """
        from order import OrderManager  # local import avoids import cycle at load time

        data = {
            "config": self._config(),
            "funds": self.funds,
            "tick": self.current_tick,
            "riders": [rider.to_dict() for rider in self.riders],
            "orders": [order.to_dict() for order in globalvar.get_value("orders", [])],
        ()
        }
        with open(path, "w", encoding="utf-8") as handle:
            json.dump(data, handle, indent=2)
        logger.info("State saved to %s", path)
        return path
