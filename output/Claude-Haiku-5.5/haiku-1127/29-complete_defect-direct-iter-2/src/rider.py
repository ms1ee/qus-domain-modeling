"""Rider model: state machine, street-grid movement and event logging.

A rider is idle (0) until an order is appended to ``orders``. On the next
tick it accepts the order and drives to the restaurant (1). After arriving
it drives to the customer (2). Completing the delivery returns it to idle.
"""

import logging

import globalvar
from config import HUB_POSITION, SETTINGS
from order_model import (STATUS_COMPLETED, STATUS_DELIVERING,
                         STATUS_PICKING_UP)
from path_planner import PathPlanner

logger = logging.getLogger(__name__)

IDLE = 0
PICKING_UP = 1
DELIVERING = 2
STATE_NAMES = {IDLE: "idle", PICKING_UP: "picking up",
               DELIVERING: "delivering"}

MAX_LOG_ENTRIES = 5000
_planner = PathPlanner()


class Rider:
    """A delivery rider that moves across the street grid.

    Attributes:
        rider_id: Unique identifier.
        x, y: Current integer coordinates.
        speed: Movement in units per tick.
        state: 0 idle, 1 picking up, 2 delivering.
        orders: Assigned orders; the first one is the active order.
        special_case: True while moving straight toward a target that is
            directly above, below, or beside the rider.
        path: Remaining waypoints for the current leg.
        wait_ticks: Ticks spent yielding to a stationary rider.
        log: Status-change records, each a dict with "event", "order_id",
            "tick", "x", "y" and "state" keys.
    """

    def __init__(self, rider_id, speed=None):
        """Create a rider at the hub and log its spawn.

        Args:
            rider_id: Unique integer identifier.
            speed: Optional speed in units per tick. Defaults to the
                configured default rider speed.

        Raises:
            ValueError: If the speed is not positive.
        """
        self.rider_id = int(rider_id)
        self.x, self.y = HUB_POSITION
        if speed is None:
            speed = SETTINGS["default_rider_speed"]
        self.speed = int(speed)
        if self.speed <= 0:
            raise ValueError("rider speed must be positive")
        self.state = IDLE
        self.orders = []
        self.special_case = False
        self.path = []
        self.wait_ticks = 0
        self.log = []
        self._record("spawn", None)

    @property
    def position(self):
        """Current position as a tuple ``(x, y)``."""
        return (self.x, self.y)

    def current_order(self):
        """Return the order currently being served.

        Returns:
            The first assigned Order, or None if the rider has no orders.
        """
        return self.orders[0] if self.orders else None

    def move(self):
        """Advance this rider by one tick.

        Handles state transitions (idle to picking up, picking up to
        delivering, delivering to idle) and movement along the route. All
        status-change log entries are written here.
        """
        if self.state == IDLE:
            order = self.current_order()
            if order is None:
                return
            self._accept_order(order)
        elif self.current_order() is None:
            logger.warning("Rider #%d had no order while busy; idling",
                           self.rider_id)
            self.state = IDLE
            self.path = []
            return

        budget = self.speed
        while True:
            if not self.path:
                if self.state == PICKING_UP:
                    self._arrive_at_merchant()
                    continue
                self._deliver()
                return
            if budget <= 0 or self._is_blocked():
                return
            budget = self._step(budget)

    def _accept_order(self, order):
        """Start serving an order: idle to picking up.

        Args:
            order: The Order being accepted.
        """
        self.state = PICKING_UP
        order.status = STATUS_PICKING_UP
        self.path = _planner.plan(self.position, order.res_pos)
        self.special_case = False
        self.wait_ticks = 0
        self._record("accepted_order", order.id)

    def _arrive_at_merchant(self):
        """Handle arrival at the restaurant: picking up to delivering."""
        order = self.current_order()
        order.picked_up_tick = globalvar.get_value("tick") or 0
        order.status = STATUS_DELIVERING
        self.state = DELIVERING
        self.path = _planner.plan(self.position, order.cus_pos)
        self._record("arrived_at_merchant", order.id)

    def _deliver(self):
        """Handle delivery completion: delivering to idle.

        Removes the order from the rider, marks it completed, credits the
        order fee to the system funds and returns the rider to idle.
        """
        order = self.orders.pop(0)
        tick = globalvar.get_value("tick") or 0
        order.complete(tick)
        self.state = IDLE
        self.path = []
        self.special_case = False
        self.wait_ticks = 0
        funds = globalvar.get_value("funds") or 0
        globalvar.set_value("funds", funds + SETTINGS["order_fee"])
        self._record("delivered_to_customer", order.id)

    def _is_blocked(self):
        """Decide whether to yield to a stationary rider on the next waypoint.

        To avoid path conflicts a moving rider waits while another rider
        sits on its next waypoint. After ``max_wait_ticks`` the rider
        proceeds anyway, which prevents deadlock.

        Returns:
            True if this rider should wait this tick.
        """
        target = self.path[0]
        occupied = False
        for other in globalvar.get_value("riders") or []:
            if other is not self and not other.path and \
                    other.position == target:
                occupied = True
                break
        if not occupied:
            self.wait_ticks = 0
            return False
        if self.wait_ticks >= SETTINGS["max_wait_ticks"]:
            logger.debug("Rider #%d breaks deadlock at %s",
                         self.rider_id, target)
            return False
        self.wait_ticks += 1
        return True

    def _step(self, budget):
        """Move along the next leg using up to ``budget`` units.

        Legs are axis-aligned, so the rider moves horizontally then
        vertically toward the waypoint.

        Args:
            budget: Remaining movement units for this tick.

        Returns:
            Remaining movement units after this step.
        """
        target_x, target_y = self.path[0]
        if (self.x, self.y) == (target_x, target_y):
            self.path.pop(0)
            return budget

        final_x, final_y = self.path[-1]
        self.special_case = ((self.x == final_x or self.y == final_y)
                             and self.position != (final_x, final_y))

        delta_x = target_x - self.x
        delta_y = target_y - self.y
        if delta_x:
            step = min(budget, abs(delta_x))
            self.x += step if delta_x > 0 else -step
            budget -= step
        if delta_y and budget > 0:
            step = min(budget, abs(delta_y))
            self.y += step if delta_y > 0 else -step
            budget -= step

        if (self.x, self.y) == (target_x, target_y):
            self.path.pop(0)
        return budget

    def _record(self, event, order_id):
        """Append a status-change entry to the rider log.

        Args:
            event: One of "spawn", "accepted_order", "arrived_at_merchant",
                "delivered_to_customer".
            order_id: Related order ID, or None.
        """
        entry = {
            "event": event,
            "order_id": order_id,
            "tick": globalvar.get_value("tick") or 0,
            "x": self.x,
            "y": self.y,
            "state": self.state,
        }
        self.log.append(entry)
        if len(self.log) > MAX_LOG_ENTRIES:
            del self.log[:len(self.log) - MAX_LOG_ENTRIES]
        logger.debug("Rider #%d %s order=%s at (%d,%d)", self.rider_id,
                     event, order_id, self.x, self.y)

    def to_dict(self):
        """Return a JSON-serialisable representation of the rider.

        Returns:
            Dictionary of rider fields.
        """
        return {
            "rider_id": self.rider_id,
            "x": self.x,
            "y": self.y,
            "speed": self.speed,
            "state": self.state,
            "orders": [order.id for order in self.orders],
            "special_case": self.special_case,
            "log": list(self.log),
        }
