"""System initialization, rider recruitment and the main simulation clock."""

import json
import logging
import os

import globalvar
from globalvar import get_value, set_value
from order import OrderManager, find_best_rider_for_order
from order_model import ACTIVE_ORDER_STATUSES, ORDER_PENDING, Order
from path_planner import MAP_SIZE
from rider import STATE_IDLE, Rider

logger = logging.getLogger(__name__)

CONFIG_VERSION = 1

# Configurable parameters (may be overridden through the JSON config file).
PARAMS = {
    "initial_funds": 1000,
    "recruit_min_funds": 300,
    "recruit_cost": 500,
}


def init_system():
    """Initialize the global variables of the dispatch system.

    Sets system funds, an empty rider list, the rider ID counter, the
    running state, the simulated tick and an empty order history.
    """
    globalvar._init()
    set_value("funds", PARAMS["initial_funds"])
    set_value("riders", [])
    set_value("rider_id_counter", 0)
    set_value("running", True)
    set_value("tick", 0)
    set_value("orders", [])
    logger.debug("System initialized")


class SystemManager:
    """Core coordinator for funds, riders, orders and the simulation clock."""

    def __init__(self):
        """Initialize global state and the order manager."""
        init_system()
        self.order_manager = OrderManager()

    # ----- basic state accessors -------------------------------------------
    @property
    def funds(self):
        """Current system funds (integer, may be negative)."""
        return get_value("funds", 0)

    @funds.setter
    def funds(self, value):
        set_value("funds", int(value))

    @property
    def riders(self):
        """The dynamic rider list stored in the global variables."""
        riders = get_value("riders")
        if riders is None:
            riders = []
            set_value("riders", riders)
        return riders

    def current_tick(self):
        """Return the current simulation tick."""
        return get_value("tick", 0) or 0

    def is_running(self):
        """Return the running flag that controls the main loop."""
        return bool(get_value("running", False))

    def stop(self):
        """Clear the running flag so the main loop terminates."""
        set_value("running", False)

    def find_rider(self, rider_id):
        """Return the rider with ``rider_id`` or None."""
        for rider in self.riders:
            if rider.rider_id == rider_id:
                return rider
        return None

    # ----- rider management ------------------------------------------------
    def _next_rider_id(self):
        """Increment and return the rider ID counter."""
        counter = (get_value("rider_id_counter", 0) or 0) + 1
        set_value("rider_id_counter", counter)
        return counter

    def add_rider(self):
        """Create a rider at (400, 400) and add it to the rider list.

        Returns:
            The newly created ``Rider``.
        """
        rider = Rider(self._next_rider_id())
        self.riders.append(rider)
        logger.info("Rider %d recruited", rider.rider_id)
        return rider

    def idle_rider_count(self):
        """Return the number of riders without active orders."""
        return sum(1 for r in self.riders if r.is_idle())

    def pending_order_count(self):
        """Return the number of orders waiting for a rider."""
        return len(self.order_manager.pending_orders())

    def maybe_recruit(self):
        """Recruit a new rider when funds and demand allow it.

        Trigger: funds >= 300 and pending orders > idle riders.
        Cost: 500, deducted from system funds.

        Returns:
            The new ``Rider`` if one was recruited, otherwise None.
        """
        if self.funds >= PARAMS["recruit_min_funds"] and \
                self.pending_order_count() > self.idle_rider_count():
            rider = self.add_rider()
            self.funds = self.funds - PARAMS["recruit_cost"]
            return rider
        return None

    # ----- dispatching -----------------------------------------------------
    def dispatch_pending(self):
        """Assign every pending order to the best rider, recruiting if needed.

        Returns:
            List of ``(order, rider)`` tuples for orders assigned in this call.
        """
        tick = self.current_tick()
        assignments = []
        for order in self.order_manager.pending_orders():
            self.maybe_recruit()
            rider = find_best_rider_for_order(order)
            if rider is None:
                continue
            self.order_manager.assign(order, rider, tick)
            assignments.append((order, rider))
        return assignments

    def submit_order(self, restaurant, customer):
        """Create an order from user input and dispatch it.

        Args:
            restaurant: ``(x, y)`` restaurant coordinates.
            customer: ``(x, y)`` customer coordinates.

        Returns:
            Tuple ``(order, rider, new_rider)``: the order, the assigned rider
            (None if no rider could be assigned) and whether a rider was
            recruited by this submission.
        """
        before = len(self.riders)
        order = self.order_manager.create_order(restaurant, customer, self.current_tick())
        self.dispatch_pending()
        new_rider = len(self.riders) > before
        rider = self.find_rider(order.rider_id) if order.rider_id is not None else None
        return order, rider, new_rider

    # ----- simulation clock ------------------------------------------------
    def has_active_orders(self):
        """Return True if any order is assigned or in progress."""
        return any(o.status in ACTIVE_ORDER_STATUSES for o in self.order_manager.all_orders())

    def tick(self):
        """Advance the simulation by one unit of time.

        Returns:
            Number of orders completed during this tick.
        """
        set_value("tick", self.current_tick() + 1)
        completed_before = len(self.order_manager.completed_orders())
        self.dispatch_pending()
        for rider in list(self.riders):
            rider.move()
        return len(self.order_manager.completed_orders()) - completed_before

    # ----- consistency -----------------------------------------------------
    def check_consistency(self):
        """Verify internal invariants and report problems.

        Returns:
            List of human-readable issue descriptions (empty when consistent).
        """
        issues = []
        funds = get_value("funds")
        if not isinstance(funds, int):
            issues.append("system funds is not an integer")
        ids = [r.rider_id for r in self.riders]
        if len(set(ids)) != len(ids):
            issues.append("duplicate rider IDs detected")
        rider_ids = set(ids)
        for rider in self.riders:
            if not (0 <= rider.x <= MAP_SIZE and 0 <= rider.y <= MAP_SIZE):
                issues.append(f"rider {rider.rider_id} is outside the map")
        for order in self.order_manager.all_orders():
            if order.status == ORDER_PENDING and order.rider_id is not None:
                issues.append(f"order {order.id} is pending but has a rider")
            if order.status in ACTIVE_ORDER_STATUSES and order.rider_id not in rider_ids:
                issues.append(f"order {order.id} references unknown rider {order.rider_id}")
        return issues

    # ----- persistence -----------------------------------------------------
    def save_config(self, path):
        """Save parameters, state, riders and order history as JSON.

        The file is written to a temporary name and then atomically replaced.

        Args:
            path: Destination file path.

        Raises:
            OSError: If the file cannot be written.
        """
        data = {
            "version": CONFIG_VERSION,
            "parameters": dict(PARAMS),
            "state": {
                "funds": self.funds,
                "rider_id_counter": get_value("rider_id_counter", 0),
                "tick": self.current_tick(),
            },
            "riders": [r.to_dict() for r in self.riders],
            "orders": [o.to_dict() for o in self.order_manager.all_orders()],
        }
        tmp_path = path + ".tmp"
        with open(tmp_path, "w", encoding="utf-8") as handle:
            json.dump(data, handle, indent=2)
        os.replace(tmp_path, path)
        logger.info("Configuration saved to %s", path)

    def load_config(self, path):
        """Load a JSON configuration file, replacing the current state.

        The state is only replaced after the whole file has been parsed
        successfully, so a bad file leaves the running system untouched.

        Args:
            path: Source file path.

        Raises:
            OSError: If the file cannot be read.
            ValueError: If the file content is malformed.
        """
        with open(path, encoding="utf-8") as handle:
            try:
                data = json.load(handle)
            except json.JSONDecodeError as exc:
                raise ValueError(f"Invalid JSON in {path}: {exc}") from exc
        if not isinstance(data, dict):
            raise ValueError("Configuration root must be a JSON object.")

        params = dict(PARAMS)
        for key, value in data.get("parameters", {}).items():
            if key in params:
                params[key] = int(value)

        state = data.get("state", {})
        funds = int(state.get("funds", params["initial_funds"]))
        counter = int(state.get("rider_id_counter", 0))
        tick = int(state.get("tick", 0))

        orders = [Order.from_dict(d) for d in data.get("orders", [])]
        orders_by_id = {o.id: o for o in orders}
        riders = [Rider.from_dict(d, orders_by_id) for d in data.get("riders", [])]

        PARAMS.update(params)
        set_value("funds", funds)
        set_value("rider_id_counter", counter)
        set_value("tick", tick)
        set_value("orders", orders)
        set_value("riders", riders)
        logger.info("Configuration loaded from %s", path)
