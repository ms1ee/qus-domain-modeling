"""System state management, rider recruitment and simulation control."""

import json
import logging

import globalvar
from globalvar import get_value, set_value
from order import OrderManager, find_best_rider_for_order
from rider import Rider, STATE_IDLE

logger = logging.getLogger(__name__)

INITIAL_FUNDS = 1000
RECRUIT_FUNDS_THRESHOLD = 300
RECRUIT_COST = 300


def init_system():
    """Initialise the global variables with the default system parameters.

    Sets funds to 1000, an empty rider list, rider id counter to 0, the
    running flag to True and the simulated tick to 0.
    """
    globalvar._init()
    set_value("funds", INITIAL_FUNDS)
    set_value("rider_id_counter", 0)
    set_value("is_running", True)
    set_value("current_tick", 0)
    set_value("riders", [])
    logger.info("System initialised with funds=%d", INITIAL_FUNDS)


def _make_property(key, default):
    """Create a property that reads and writes a global variable."""
    return property(
        lambda self: get_value(key, default),
        lambda self, value: set_value(key, value),
    )


class SystemManager:
    """Core manager for funds, riders, orders and the simulation loop.

    Attributes:
        order_manager: The ``OrderManager`` owned by the system.
        funds: System funds (may be negative).
        rider_id_counter: Last issued rider id.
        is_running: Main loop control flag.
        current_tick: Number of simulated ticks elapsed.
    """

    funds = _make_property("funds", 0)
    rider_id_counter = _make_property("rider_id_counter", 0)
    is_running = _make_property("is_running", False)
    current_tick = _make_property("current_tick", 0)

    def __init__(self):
        """Create the manager, initialising global state if needed."""
        if get_value("funds") is None:
            init_system()
        if get_value("riders") is None:
            set_value("riders", [])
        self.order_manager = OrderManager()

    @property
    def riders(self):
        """Return the live list of riders."""
        return get_value("riders")

    def idle_riders(self):
        """Return riders that are idle and hold no orders."""
        return [r for r in self.riders if r.state == STATE_IDLE and not r.orders]

    def recruit_rider(self):
        """Create a new rider, charging the recruitment cost.

        Returns:
            The newly created ``Rider``.
        """
        self.rider_id_counter = self.rider_id_counter + 1
        rider = Rider(self.rider_id_counter)
        self.riders.append(rider)
        self.funds = self.funds - RECRUIT_COST
        logger.info("Recruited rider %d (funds now %d)", rider.rider_id, self.funds)
        return rider

    def _recruit_if_needed(self, pending_count):
        """Recruit riders while pending orders exceed idle riders and funds allow.

        Args:
            pending_count: Number of orders waiting for a rider.

        Returns:
            List of riders created during this call.
        """
        created = []
        while self.funds >= RECRUIT_FUNDS_THRESHOLD and pending_count > len(self.idle_riders()):
            created.append(self.recruit_rider())
        return created

    def _try_assign(self, order):
        """Assign ``order`` to the best available rider if one exists.

        Returns:
            The assigned ``Rider``, or None.
        """
        rider = find_best_rider_for_order(order)
        if rider is not None:
            self.order_manager.assign(order, rider)
        return rider

    def submit_order(self, restaurant_pos, customer_pos):
        """Create an order, recruit a rider if needed and assign the order.

        Args:
            restaurant_pos: Restaurant ``(x, y)`` in range 0-800.
            customer_pos: Customer ``(x, y)`` in range 0-800.

        Returns:
            Dictionary with keys ``order``, ``rider`` (or None) and
            ``new_rider`` (bool).

        Raises:
            OrderValidationError: If coordinates are invalid.
        """
        order = self.order_manager.create_order(restaurant_pos, customer_pos, self.current_tick)
        created = self._recruit_if_needed(len(self.order_manager.pending_orders()))
        rider = self._try_assign(order)
        return {"order": order, "rider": rider, "new_rider": bool(created)}

    def tick(self):
        """Advance the simulation by one tick.

        Every rider moves one step, and pending orders are retried for
        assignment (with recruitment when needed). Exceptions raised by a
        rider are logged and the rider's state is repaired, so the rest of
        the system keeps running.
        """
        self.current_tick = self.current_tick + 1
        for rider in list(self.riders):
            try:
                rider.move()
            except Exception:  # error recovery: keep simulating other riders
                logger.exception("Rider %d failed during tick; recovering.", rider.rider_id)
                rider.check_consistency()
        pending = self.order_manager.pending_orders()
        if pending:
            self._recruit_if_needed(len(pending))
            for order in pending:
                self._try_assign(order)

    def stop(self):
        """Request that the main loop terminate."""
        self.is_running = False

    def snapshot(self):
        """Return the full system state as a JSON-serialisable dictionary."""
        return {
            "funds": self.funds,
            "rider_id_counter": self.rider_id_counter,
            "current_tick": self.current_tick,
            "riders": [r.to_dict() for r in self.riders],
            "orders": self.order_manager.to_list(),
        }

    def save_snapshot(self, path):
        """Write the current state to a JSON file.

        Args:
            path: Destination file path.

        Raises:
            OSError: If the file cannot be written.
        """
        with open(path, "w", encoding="utf-8") as handle:
            json.dump(self.snapshot(), handle, indent=2)
        logger.info("Snapshot saved to %s", path)
