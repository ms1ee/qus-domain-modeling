"""System manager: funds, rider pool, order dispatch and simulation clock."""

import json
import logging
import os

import globalvar
from grid_map import GridMap
from order import OrderManager
from path_planner import PathPlanner
from rider import Rider

logger = logging.getLogger(__name__)

DEFAULT_CONFIG = {
    "initial_funds": 1000,
    "recruit_threshold": 300,
    "recruit_cost": 500,
    "map_size": 800,
    "cell_size": 100,
}
DEFAULT_CONFIG_PATH = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "config.json"
)


def _global_property(key, doc):
    """Create a property that reads and writes a global variable."""

    def getter(self):
        return globalvar.get_value(key)

    def setter(self, value):
        globalvar.set_value(key, value)

    return property(getter, setter, doc=doc)


def load_config(path=None):
    """Load system parameters from a JSON file, falling back to defaults.

    Args:
        path: Optional path to a JSON configuration file.

    Returns:
        A dict of configuration values.
    """
    config = dict(DEFAULT_CONFIG)
    path = path or DEFAULT_CONFIG_PATH
    if not os.path.exists(path):
        logger.info("No config file at %s; using defaults", path)
        return config
    try:
        with open(path, encoding="utf-8") as handle:
            data = json.load(handle)
    except (OSError, json.JSONDecodeError) as exc:
        logger.error("Could not read config %s: %s", path, exc)
        return config
    if not isinstance(data, dict):
        logger.error("Config %s must contain a JSON object", path)
        return config
    for key, value in data.items():
        if key in DEFAULT_CONFIG and isinstance(value, int) \
                and not isinstance(value, bool):
            config[key] = value
    if (config["recruit_cost"] <= 0 or config["cell_size"] <= 0
            or config["map_size"] % config["cell_size"] != 0):
        logger.error("Invalid grid/cost configuration; using defaults")
        return dict(DEFAULT_CONFIG)
    return config


class SystemManager:
    """Core manager for funds, riders, orders and the simulation clock.

    Funds, riders, rider ID counter, running flag and tick are stored in
    :mod:`globalvar` so that all modules share one source of truth.
    """

    funds = _global_property("funds", "System fund balance (int).")
    riders = _global_property("riders", "List of Rider objects.")
    rider_id_counter = _global_property("rider_id_counter",
                                        "Last issued rider ID.")
    running = _global_property("running", "Main loop running flag.")
    tick = _global_property("tick", "Simulated time in ticks.")

    def __init__(self, config=None):
        """Create the system manager.

        Args:
            config: Optional configuration dict (see ``DEFAULT_CONFIG``).
        """
        self.config = dict(config or DEFAULT_CONFIG)
        self.grid = GridMap(self.config["map_size"], self.config["cell_size"])
        self.path_planner = PathPlanner(self.grid)
        self.order_manager = OrderManager()
        globalvar.set_value("order_manager", self.order_manager)
        globalvar.set_value("config", self.config)

    def find_rider(self, rider_id):
        """Return the rider with ``rider_id``, or None."""
        for rider in self.riders:
            if rider.rider_id == rider_id:
                return rider
        return None

    def idle_riders(self):
        """Return riders that have no work assigned."""
        return [r for r in self.riders if r.is_idle()]

    def recruit_rider(self):
        """Create a new rider, deducting the recruitment cost.

        Returns:
            The newly created :class:`Rider`.
        """
        self.funds = self.funds - self.config["recruit_cost"]
        self.rider_id_counter = self.rider_id_counter + 1
        rider = Rider(self.rider_id_counter)
        self.riders.append(rider)
        logger.info("Recruited rider %d; funds now %d",
                    rider.rider_id, self.funds)
        return rider

    def maybe_recruit(self, pending_count):
        """Recruit riders while funds allow and pending orders exceed idle riders.

        Args:
            pending_count: Number of orders waiting for assignment.

        Returns:
            True if at least one rider was recruited.
        """
        recruited = False
        while (self.funds >= self.config["recruit_threshold"]
               and pending_count > len(self.idle_riders())):
            self.recruit_rider()
            recruited = True
        return recruited

    def dispatch_pending(self):
        """Assign all pending orders, recruiting riders when required.

        Returns:
            List of ``(order, rider)`` tuples for orders assigned this call.
        """
        assigned = []
        for order in list(self.order_manager.pending_orders()):
            self.maybe_recruit(len(self.order_manager.pending_orders()))
            rider = self.order_manager.assign_order(order)
            if rider is None:
                break
            assigned.append((order, rider))
        return assigned

    def submit_order(self, restaurant_x, restaurant_y, customer_x, customer_y):
        """Create an order and dispatch it immediately.

        Returns:
            Tuple ``(order, rider, recruited)``. ``rider`` is None if no rider
            could be assigned; ``recruited`` is True if a new rider was added.
        """
        order = self.order_manager.create_order(
            restaurant_x, restaurant_y, customer_x, customer_y
        )
        before = len(self.riders)
        self.dispatch_pending()
        recruited = len(self.riders) > before
        rider = self.find_rider(order.rider_id) if order.rider_id else None
        return order, rider, recruited

    def advance_tick(self):
        """Advance the simulation by one unit of time.

        Every rider moves one step; exceptions are isolated per rider and the
        rider is recovered. Pending orders are then dispatched.

        Returns:
            The new tick value.
        """
        self.tick = (self.tick or 0) + 1
        for rider in list(self.riders):
            try:
                rider.move()
            except Exception:  # pylint: disable=broad-except
                logger.exception("Error moving rider %d", rider.rider_id)
                rider.recover()
        try:
            self.dispatch_pending()
        except Exception:  # pylint: disable=broad-except
            logger.exception("Error dispatching pending orders")
        return self.tick

    def check_consistency(self):
        """Check internal state invariants.

        Returns:
            List of human-readable issue strings (empty when consistent).
        """
        issues = []
        rider_ids = {r.rider_id for r in self.riders}
        if len(rider_ids) != len(self.riders):
            issues.append("duplicate rider IDs detected")
        for rider in self.riders:
            if rider.state != 0 and rider.current_order is None:
                issues.append(f"rider {rider.rider_id} busy without order")
            if rider.current_order is not None \
                    and rider.current_order.status == "completed":
                issues.append(
                    f"rider {rider.rider_id} holds a completed order")
        for order in self.order_manager.orders:
            if order.rider_id is not None and order.rider_id not in rider_ids:
                issues.append(f"order {order.id} assigned to unknown rider")
        return issues

    def save_state(self, path):
        """Write funds, riders, orders and config to a JSON file.

        Args:
            path: Destination file path.

        Raises:
            OSError: If the file cannot be written.
        """
        data = {
            "funds": self.funds,
            "tick": self.tick,
            "rider_id_counter": self.rider_id_counter,
            "config": self.config,
            "riders": [r.to_dict() for r in self.riders],
            "orders": [o.to_dict() for o in self.order_manager.orders],
        }
        with open(path, "w", encoding="utf-8") as handle:
            json.dump(data, handle, indent=2)
        logger.info("State saved to %s", path)


def init_system(config_path=None):
    """Initialise global variables and create the system manager.

    Args:
        config_path: Optional path to a JSON configuration file.

    Returns:
        The initialised :class:`SystemManager`.
    """
    globalvar._init()  # pylint: disable=protected-access
    config = load_config(config_path)
    globalvar.set_value("funds", config["initial_funds"])
    globalvar.set_value("riders", [])
    globalvar.set_value("rider_id_counter", 0)
    globalvar.set_value("running", True)
    globalvar.set_value("tick", 0)
    return SystemManager(config)
