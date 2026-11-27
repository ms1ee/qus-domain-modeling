"""Rider model: state machine, movement and event logging.

Rider states:
    0 (IDLE): available, no active order.
    1 (PICKING_UP): en route to the restaurant.
    2 (DELIVERING): en route to the customer.

Events recorded in ``Rider.log``:
    "spawn", "accepted_order", "arrived_at_merchant", "delivered_to_customer".
"""

import logging

import globalvar
from path_planner import MAP_SIZE, PathPlanner

LOGGER = logging.getLogger("dispatch.rider")

IDLE = 0
PICKING_UP = 1
DELIVERING = 2
STATE_NAMES = {IDLE: "idle", PICKING_UP: "picking up", DELIVERING: "delivering"}

DEFAULT_RIDER_SPEED = 20
SPAWN_X = 400
SPAWN_Y = 400


class Rider:
    """A delivery rider that moves along streets and serves orders."""

    def __init__(self, rider_id, speed=DEFAULT_RIDER_SPEED):
        """Create a rider spawned at (400, 400) in the idle state.

        Args:
            rider_id: Unique integer identifier.
            speed: Movement speed in units per tick.
        """
        self.rider_id = int(rider_id)
        self.x = SPAWN_X
        self.y = SPAWN_Y
        self.speed = int(speed)
        self.state = IDLE
        self.orders = []
        self.special_case = False
        self.log = []
        self._log_event("spawn", None)

    # ------------------------------------------------------------------
    # Logging and queries
    # ------------------------------------------------------------------
    def _log_event(self, event, order_id):
        """Append a status-change record to the rider log."""
        self.log.append({
            "time": globalvar.current_tick(),
            "event": event,
            "order_id": order_id,
            "rider_id": self.rider_id,
            "x": self.x,
            "y": self.y,
        })

    def state_name(self):
        """Return the human-readable name of the current state."""
        return STATE_NAMES.get(self.state, "unknown")

    def current_order(self):
        """Return the first order that is not completed, or None."""
        for order in self.orders:
            if order.status != "completed":
                return order
        return None

    def active_order_count(self):
        """Return the number of orders not yet completed."""
        return sum(1 for order in self.orders if order.status != "completed")

    def is_idle(self):
        """Return True if the rider has no active order."""
        return self.active_order_count() == 0

    # ------------------------------------------------------------------
    # State transitions and movement
    # ------------------------------------------------------------------
    def _accept(self, order):
        """Transition from idle (or after a delivery) to picking up."""
        self.state = PICKING_UP
        order.status = "picking_up"
        self._log_event("accepted_order", order.id)

    def _target(self, order):
        """Return the destination for the current state."""
        if self.state == DELIVERING:
            return order.customer_x, order.customer_y
        return order.restaurant_x, order.restaurant_y

    def _handle_arrival(self, order):
        """Apply state transitions when the rider reaches a destination."""
        pos = (self.x, self.y)
        if self.state == PICKING_UP and pos == (order.restaurant_x, order.restaurant_y):
            self.state = DELIVERING
            order.status = "delivering"
            self._log_event("arrived_at_merchant", order.id)
        elif self.state == DELIVERING and pos == (order.customer_x, order.customer_y):
            order.complete(globalvar.current_tick())
            self._log_event("delivered_to_customer", order.id)
            next_order = self.current_order()
            if next_order is None:
                self.state = IDLE
                self.special_case = False
            else:
                self._accept(next_order)

    def move(self):
        """Advance the rider by one tick.

        Performs the idle-to-picking-up transition when a new order is
        assigned, moves toward the current destination along streets, and
        applies arrival transitions.
        """
        order = self.current_order()
        if order is None:
            self.state = IDLE
            self.special_case = False
            return
        if self.state == IDLE:
            self._accept(order)
        target_x, target_y = self._target(order)
        # Special case: rider is directly above/below or beside the target.
        self.special_case = self.x == target_x or self.y == target_y
        self.x, self.y = PathPlanner.next_position(
            self.x, self.y, target_x, target_y, self.speed)
        self._handle_arrival(order)

    def recover(self):
        """Repair an inconsistent rider after an unexpected error."""
        if self.state not in STATE_NAMES:
            LOGGER.warning("Rider %s had invalid state %s; resetting",
                           self.rider_id, self.state)
            self.state = IDLE
        if not (0 <= self.x <= MAP_SIZE and 0 <= self.y <= MAP_SIZE):
            LOGGER.warning("Rider %s was off-map; returning to spawn", self.rider_id)
            self.x, self.y = SPAWN_X, SPAWN_Y
        order = self.current_order()
        if order is None:
            self.state = IDLE
            self.special_case = False
        elif self.state == IDLE:
            self._accept(order)

    def to_dict(self):
        """Return a JSON-serialisable summary of the rider."""
        return {
            "rider_id": self.rider_id,
            "x": self.x,
            "y": self.y,
            "speed": self.speed,
            "state": self.state,
            "special_case": self.special_case,
            "order_ids": [order.id for order in self.orders],
        }
