"""Rider model: state machine, movement and event logging.

Rider states:
    0 = IDLE          available for new orders
    1 = PICKING_UP    en route to the restaurant
    2 = DELIVERING    en route to the customer

Logged events (Rider.log entries, keys include "event" and "order_id"):
    "spawn", "accepted_order", "arrived_at_merchant", "delivered_to_customer"
"""

import logging
import math
from typing import List, Optional

from globalvar import get_value
from order_model import STATUS_COMPLETED, STATUS_DELIVERING
from path_planner import PathPlanner

logger = logging.getLogger("dispatch.rider")

IDLE = 0
PICKING_UP = 1
DELIVERING = 2
STATE_NAMES = {IDLE: "idle", PICKING_UP: "picking up", DELIVERING: "delivering"}

DEFAULT_SPEED = 20
START_X = 400
START_Y = 400

EVENT_SPAWN = "spawn"
EVENT_ACCEPTED = "accepted_order"
EVENT_ARRIVED = "arrived_at_merchant"
EVENT_DELIVERED = "delivered_to_customer"

_PLANNER = PathPlanner()


def _current_tick() -> int:
    """Return the simulated time from the global store."""
    return int(get_value("current_tick") or 0)


class Rider:
    """A delivery rider that serves one or more orders."""

    def __init__(self, rider_id: int, x: int = START_X, y: int = START_Y,
                 speed: int = DEFAULT_SPEED) -> None:
        """Create a rider and log its spawn event.

        Args:
            rider_id: Unique identifier.
            x: Initial x coordinate (on a street).
            y: Initial y coordinate (on a street).
            speed: Movement speed in units per tick.
        """
        self.rider_id: int = int(rider_id)
        self.x: int = int(x)
        self.y: int = int(y)
        self.speed: int = int(speed)
        self.state: int = IDLE
        self.orders: list = []
        self.special_case: bool = False
        self.log: List[dict] = []
        self._path: List[tuple] = []
        self._path_target: Optional[tuple] = None
        self._record(EVENT_SPAWN, None)
        logger.info("Rider %d spawned at (%d, %d)", self.rider_id, self.x, self.y)

    @property
    def position(self) -> tuple:
        """Current (x, y) position."""
        return self.x, self.y

    def current_order(self):
        """Return the earliest order that is not yet completed, or None."""
        for order in self.orders:
            if order.status != STATUS_COMPLETED:
                return order
        return None

    def active_orders(self) -> list:
        """Return all orders that are not yet completed."""
        return [o for o in self.orders if o.status != STATUS_COMPLETED]

    def distance_to(self, x: float, y: float) -> float:
        """Return the Euclidean distance from the rider to a point."""
        return math.hypot(self.x - x, self.y - y)

    def accept_order(self, order) -> None:
        """Accept an order: queue it, and start picking up if idle.

        Args:
            order: Order to add to this rider's list.
        """
        self.orders.append(order)
        order.assign_to(self.rider_id)
        if self.state == IDLE:
            self.state = PICKING_UP
            self._path = []
            self._path_target = None
        if not order.route or order.route[-1] != (self.x, self.y):
            order.route.append((self.x, self.y))
        self._record(EVENT_ACCEPTED, order.id)

    def move(self) -> None:
        """Advance the rider by one tick.

        Performs movement along streets toward the current target
        (restaurant while picking up, customer while delivering) and
        applies state transitions upon arrival.
        """
        if self.state == IDLE:
            self.special_case = False
            return
        order = self.current_order()
        if order is None:
            self._set_idle()
            return
        target = self._target_for(order)
        if self._path_target != target:
            self._path = _PLANNER.plan((self.x, self.y), target)
            self._path_target = target
        if self._path:
            new_pos, self._path = _PLANNER.advance((self.x, self.y), self._path, self.speed)
            if new_pos != (self.x, self.y):
                self.x, self.y = new_pos
                order.route.append(new_pos)
        self.special_case = self.x == target[0] or self.y == target[1]
        if (self.x, self.y) == target:
            self._handle_arrival(order)

    def resynchronize(self) -> None:
        """Recover a consistent state after an unexpected error."""
        self._path = []
        self._path_target = None
        order = self.current_order()
        if order is None:
            self._set_idle()
            return
        self.state = DELIVERING if order.status == STATUS_DELIVERING else PICKING_UP
        self.special_case = False
        logger.warning("Rider %d resynchronised to state %d", self.rider_id, self.state)

    def to_dict(self) -> dict:
        """Serialise the rider to a JSON-compatible dictionary."""
        return {
            "rider_id": self.rider_id,
            "x": self.x,
            "y": self.y,
            "speed": self.speed,
            "state": self.state,
            "special_case": self.special_case,
            "order_ids": [o.id for o in self.orders],
            "active_order_ids": [o.id for o in self.active_orders()],
        }

    def _target_for(self, order) -> tuple:
        """Return the destination point for the rider's current phase."""
        if self.state == PICKING_UP:
            return order.restaurant_pos
        return order.customer_pos

    def _handle_arrival(self, order) -> None:
        """Apply state transitions when the rider reaches its target."""
        if self.state == PICKING_UP:
            self.state = DELIVERING
            order.mark_delivering()
            self._path = []
            self._path_target = None
            self._record(EVENT_ARRIVED, order.id)
        elif self.state == DELIVERING:
            order.complete(_current_tick())
            self._path = []
            self._path_target = None
            next_order = self.current_order()
            if next_order is None:
                self._set_idle()
            else:
                self.state = PICKING_UP
            self._record(EVENT_DELIVERED, order.id)

    def _set_idle(self) -> None:
        """Return the rider to the idle state and clear movement data."""
        self.state = IDLE
        self.special_case = False
        self._path = []
        self._path_target = None

    def _record(self, event: str, order_id) -> None:
        """Append a status-change entry to the rider's log."""
        self.log.append({
            "event": event,
            "order_id": order_id,
            "rider_id": self.rider_id,
            "tick": _current_tick(),
            "x": self.x,
            "y": self.y,
            "state": self.state,
        })
