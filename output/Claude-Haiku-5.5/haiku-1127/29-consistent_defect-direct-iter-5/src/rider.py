"""Rider model: state machine, movement and per-rider event log.

State machine (rider.state):
    0 Idle        -> 1 Picking Up  : an assigned order is accepted (move()).
    1 Picking Up  -> 2 Delivering  : the rider reaches the restaurant.
    2 Delivering  -> 1 Picking Up  : an order is delivered and another is queued.
    2 Delivering  -> 0 Idle        : an order is delivered and none remain.
"""

import logging

from globalvar import get_value
from order_model import (
    ACTIVE_ORDER_STATUSES,
    ORDER_ASSIGNED,
    ORDER_COMPLETED,
    ORDER_DELIVERING,
    ORDER_PICKING_UP,
)
from path_planner import PathPlanner

logger = logging.getLogger(__name__)

RIDER_SPEED = 20
SPAWN_POSITION = (400, 400)

STATE_IDLE = 0
STATE_PICKING_UP = 1
STATE_DELIVERING = 2
STATE_NAMES = {
    STATE_IDLE: "Idle",
    STATE_PICKING_UP: "Picking Up",
    STATE_DELIVERING: "Delivering",
}


class Rider:
    """A delivery rider that moves along streets and serves orders.

    Attributes:
        rider_id: Unique integer identifier.
        x: Current x coordinate (0-800).
        y: Current y coordinate (0-800).
        speed: Movement speed in units per tick (fixed at 20).
        state: 0 idle, 1 picking up, 2 delivering.
        orders: All orders ever assigned to this rider (history kept).
        special_case: True while the rider is directly above or below its target.
        log: List of event dictionaries with keys "event", "order_id", "tick",
            "rider_id", "x", "y" and "state".
    """

    def __init__(self, rider_id, x=SPAWN_POSITION[0], y=SPAWN_POSITION[1]):
        """Create a rider and record its spawn event.

        Args:
            rider_id: Unique integer identifier.
            x: Initial x coordinate (default 400).
            y: Initial y coordinate (default 400).
        """
        self.rider_id = int(rider_id)
        self.x = int(x)
        self.y = int(y)
        self.speed = RIDER_SPEED
        self.state = STATE_IDLE
        self.orders = []
        self.special_case = False
        self.log = []
        self._record("spawn", None)

    @property
    def state_name(self):
        """Human-readable name of the current state."""
        return STATE_NAMES.get(self.state, "Unknown")

    def position(self):
        """Return the current position as a tuple ``(x, y)``."""
        return self.x, self.y

    def active_orders(self):
        """Return orders that are assigned or in progress (not completed)."""
        return [o for o in self.orders if o.status in ACTIVE_ORDER_STATUSES]

    def is_idle(self):
        """Return True when the rider has no active orders."""
        return not self.active_orders()

    def current_order(self):
        """Return the order the rider is currently serving, or None.

        Orders are served first-in, first-out.
        """
        for order in self.orders:
            if order.status in (ORDER_PICKING_UP, ORDER_DELIVERING):
                return order
        return None

    def _now(self):
        """Return the current simulation tick from the global store."""
        return get_value("tick", 0) or 0

    def _record(self, event, order_id):
        """Append an event entry to the rider log."""
        self.log.append({
            "event": event,
            "order_id": order_id,
            "tick": self._now(),
            "rider_id": self.rider_id,
            "x": self.x,
            "y": self.y,
            "state": self.state,
        })

    def _accept_new_orders(self):
        """Accept every newly assigned order and log the acceptance."""
        for order in self.orders:
            if order.status == ORDER_ASSIGNED:
                order.accept()
                self._record("accepted_order", order.id)

    def _sync_state(self):
        """Derive the rider state from the current order."""
        current = self.current_order()
        if current is None:
            self.state = STATE_IDLE
        elif current.status == ORDER_PICKING_UP:
            self.state = STATE_PICKING_UP
        else:
            self.state = STATE_DELIVERING

    def move(self):
        """Advance the rider by one tick.

        Accepts newly assigned orders, moves toward the current target
        (restaurant when picking up, customer when delivering) and performs
        the arrival state transitions with their log entries.

        Returns:
            True if the rider had a target and moved this tick, else False.
        """
        self._accept_new_orders()
        self._sync_state()

        current = self.current_order()
        if current is None:
            self.special_case = False
            return False

        if current.status == ORDER_PICKING_UP:
            target = current.res_pos
        else:
            target = current.cus_pos

        new_x, new_y, arrived = PathPlanner.next_position(
            self.x, self.y, target[0], target[1], self.speed
        )
        self.x, self.y = new_x, new_y
        self.special_case = (new_x == target[0] and new_y != target[1])

        if arrived:
            if current.status == ORDER_PICKING_UP:
                current.mark_picked_up(self._now())
                self._sync_state()
                self._record("arrived_at_merchant", current.id)
            else:
                current.complete(self._now())
                self._sync_state()
                self._record("delivered_to_customer", current.id)
        return True

    def to_dict(self):
        """Serialize the rider into a JSON-compatible dictionary.

        Returns:
            Dictionary with rider attributes, order IDs and the event log.
        """
        return {
            "rider_id": self.rider_id,
            "x": self.x,
            "y": self.y,
            "speed": self.speed,
            "state": self.state,
            "special_case": self.special_case,
            "order_ids": [o.id for o in self.orders],
            "log": list(self.log),
        }

    @classmethod
    def from_dict(cls, data, orders_by_id):
        """Rebuild a rider from ``to_dict`` output.

        Args:
            data: Dictionary produced by ``to_dict``.
            orders_by_id: Mapping of order ID to restored ``Order`` objects.

        Returns:
            A restored ``Rider`` instance.
        """
        rider = cls(int(data["rider_id"]), int(data["x"]), int(data["y"]))
        rider.state = int(data.get("state", STATE_IDLE))
        rider.special_case = bool(data.get("special_case", False))
        rider.orders = [
            orders_by_id[oid] for oid in data.get("order_ids", []) if oid in orders_by_id
        ]
        rider.log = list(data.get("log", []))
        return rider

    def __repr__(self):
        return (
            f"Rider(id={self.rider_id}, pos=({self.x}, {self.y}), "
            f"state={self.state_name!r}, orders={len(self.orders)})"
        )
