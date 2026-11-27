"""System-wide state, funds, rider recruitment and the simulation clock."""

import json
import logging
import os

import globalvar
import grid
from order import OrderManager
from rider import Rider, DEFAULT_SPEED

logger = logging.getLogger("dispatch.system")

DEFAULT_CONFIG = {
    "initial_funds": 300,
    "rider_hire_threshold": 300,
    "rider_hire_cost": 300,
    "rider_speed": DEFAULT_SPEED,
    "order_revenue": 150,
    "fuel_cost_per_100_units": 2,
}


def init_system():
    """Initialise the global variables used by the system.

    Sets an empty rider list, rider id counter 0, running state True, the
    simulation tick to 0, the default configuration and starting funds.
    """
    globalvar._init()
    globalvar.set_value("riders", [])
    globalvar.set_value("rider_id_counter", 0)
    globalvar.set_value("running", True)
    globalvar.set_value("tick", 0)
    globalvar.set_value("orders", [])
    globalvar.set_value("config", dict(DEFAULT_CONFIG))
    globalvar.set_value("funds", DEFAULT_CONFIG["initial_funds"])
    logger.info("System initialised")


class SystemManager:
    """Manage funds, riders, configuration and the simulation tick.

    Attributes:
        orders: The OrderManager used for order creation and dispatch.
    """

    def __init__(self):
        """Create the system manager and its order manager."""
        self.orders = OrderManager()

    def _config(self):
        """Return the effective configuration merged with defaults."""
        config = dict(DEFAULT_CONFIG)
        stored = globalvar.get_value("config") or {}
        config.update(stored)
        return config

    @property
    def funds(self):
        """Current system fund balance (may be negative)."""
        return globalvar.get_value("funds", 0)

    def add_funds(self, amount):
        """Add (or subtract, if negative) an amount of funds.

        Args:
            amount: Integer amount to add.
        """
        globalvar.set_value("funds", self.funds + int(amount))

    @property
    def tick_count(self):
        """Current simulation tick."""
        return globalvar.get_value("tick", 0)

    @property
    def riders(self):
        """The list of all riders."""
        return globalvar.get_value("riders")

    @property
    def running(self):
        """True while the main loop should keep running."""
        return bool(globalvar.get_value("running", False))

    def stop(self):
        """Request that the main loop terminate."""
        globalvar.set_value("running", False)

    def get_rider(self, rider_id):
        """Return the rider with the given id, or None.

        Args:
            rider_id: Identifier to look up.
        """
        for rider in self.riders:
            if rider.rider_id == rider_id:
                return rider
        return None

    def create_rider(self):
        """Create a rider with a new unique id at a spread-out spawn point.

        Returns:
            Rider: The newly created rider.
        """
        counter = (globalvar.get_value("rider_id_counter") or 0) + 1
        globalvar.set_value("rider_id_counter", counter)
        index = (counter - 1) % (grid.GRID_DIM * grid.GRID_DIM)
        x = (index % grid.GRID_DIM) * grid.CELL_SIZE + grid.CELL_HALF
        y = (index // grid.GRID_DIM) * grid.CELL_SIZE + grid.CELL_HALF
        speed = int(self._config()["rider_speed"])
        rider = Rider(counter, x, y, speed)
        self.riders.append(rider)
        return rider

    def remove_rider(self, rider_id):
        """Remove an idle rider that has no assigned orders.

        Args:
            rider_id: Identifier of the rider to remove.

        Raises:
            KeyError: If no such rider exists.
            RuntimeError: If the rider is busy.
        """
        rider = self.get_rider(rider_id)
        if rider is None:
            raise KeyError(f"rider #{rider_id} not found")
        if rider.orders or rider.state != 0:
            raise RuntimeError(f"rider #{rider_id} is busy")
        self.riders.remove(rider)
        logger.info("Rider #%d removed", rider_id)

    def try_recruit(self):
        """Recruit a rider when funds reach the hiring threshold.

        Returns:
            Rider: The recruited rider, or None if funds are below threshold.
        """
        config = self._config()
        if self.funds >= int(config["rider_hire_threshold"]):
            self.add_funds(-int(config["rider_hire_cost"]))
            rider = self.create_rider()
            logger.info("Recruited rider #%d", rider.rider_id)
            return rider
        return None

    def tick(self):
        """Advance the simulation by one tick.

        Order of operations: advance the clock, move every rider, settle
        completed orders, recruit if funds allow, then dispatch pending
        orders.
        """
        globalvar.set_value("tick", self.tick_count + 1)
        for rider in list(self.riders):
            rider.move()
        self.orders.settle_completed()
        self.try_recruit()
        self.orders.dispatch_pending()

    def load_config(self, path):
        """Load configuration overrides from a JSON file.

        Unknown keys and invalid values are ignored. Missing files and
        malformed JSON leave the defaults in place.

        Args:
            path: Path to the JSON configuration file.

        Returns:
            bool: True if the file was read successfully.
        """
        if not os.path.exists(path):
            return False
        try:
            with open(path, "r", encoding="utf-8") as handle:
                data = json.load(handle)
        except (OSError, json.JSONDecodeError) as exc:
            logger.error("Failed to load config %s: %s", path, exc)
            return False
        if not isinstance(data, dict):
            logger.error("Config %s must contain a JSON object", path)
            return False

        config = self._config()
        for key in DEFAULT_CONFIG:
            value = data.get(key)
            if isinstance(value, bool) or not isinstance(value, int):
                continue
            if value < 0:
                continue
            if key == "rider_speed" and value == 0:
                continue
            config[key] = value
        globalvar.set_value("config", config)

        if self.tick_count == 0 and not self.riders \
                and "initial_funds" in data:
            globalvar.set_value("funds", config["initial_funds"])
        logger.info("Configuration loaded from %s", path)
        return True

    def save_state(self, path):
        """Persist configuration, funds, riders and orders as JSON.

        Args:
            path: Destination file path.

        Returns:
            bool: True if the file was written successfully.
        """
        state = {
            "config": self._config(),
            "funds": self.funds,
            "tick": self.tick_count,
            "rider_id_counter": globalvar.get_value("rider_id_counter", 0),
            "riders": [rider.to_dict() for rider in self.riders],
            "orders": [order.to_dict()
                       for order in self.orders.get_all_orders()],
        }
        try:
            with open(path, "w", encoding="utf-8") as handle:
                json.dump(state, handle, indent=2)
        except OSError as exc:
            logger.error("Failed to save state to %s: %s", path, exc)
            return False
        logger.info("State saved to %s", path)
        return True
