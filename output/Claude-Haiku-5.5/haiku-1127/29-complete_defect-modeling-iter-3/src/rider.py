"""Rider entity: state machine, movement and event logging.

A rider is idle (0) until an order is appended to ``rider.orders``. It then
moves to the restaurant (state 1, picking up), then to the customer (state
2, delivering), and returns to idle after delivery. Every transition and
every movement decision is recorded in ``rider.log``.
"""

import logging
from typing import Any, Dict, List, Optional, Tuple

from globalvar import get_value, set_value
from order_model import (
    STATUS_DELIVERING,
    STATUS_PICKING_UP,
    Order,
)
from path_planner import PathPlanner

logger = logging.getLogger(__name__)

STATE_IDLE = 0
STATE_PICKING_UP = 1
STATE_DELIVERING = 2
STATE_NAMES = {
    STATE_IDLE: "idle",
    STATE_PICKING_UP: "picking up",
    STATE_DELIVERING: "delivering",
}

EVENT_SPAWN = "spawn"
EVENT_ACCEPTED = "accepted_order"
EVENT_ARRIVED = "arrived_at_merchant"
EVENT_DELIVERED = "delivered_to_customer"

SPAWN_POSITION: Tuple[int, int] = (50, 50)
DEFAULT_SPEED = 10


def _sign(value: int) -> int:
    """Return -1, 0 or 1 according to the sign of ``value``."""
    return (value > 0) - (value < 0)


class Rider:
    """A delivery rider that moves on the street grid."""

    def __init__(self, rider_id: int) -> None:
        """Create an idle rider at the spawn position.

        Args:
            rider_id: Unique rider identifier.
        """
        self.rider_id: int = rider_id
        self.x, self.y = SPAWN_POSITION
        self.speed: int = int(get_value("rider_speed", DEFAULT_SPEED))
        self.state: int = STATE_IDLE
        self.orders: List[Order] = []
        self.special_case: bool = False
        self.log: List[Dict[str, Any]] = []
        self.path: List[Tuple[int, int]] = []
        self.stall_count: int = 0
        self._planner = PathPlanner()
        self._record(EVENT_SPAWN, None)

    # ------------------------------------------------------------------
    # Logging helpers
    # ------------------------------------------------------------------
    def _record(self, event: str, order_id: Optional[int]) -> None:
        """Append a log entry describing the current rider status.

        Args:
            event: Event name (spawn, accepted_order, ...).
            order_id: Related order identifier, or None.
        """
        entry = {
            "event": event,
            "order_id": order_id,
            "tick": int(get_value("current_tick", 0)),
            "rider_id": self.rider_id,
            "x": self.x,
            "y": self.y,
            "state": self.state,
        }
        self.log.append(entry)
        logger.debug("Rider %s: %s (order=%s)", self.rider_id, event, order_id)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------
    def move(self) -> None:
        """Advance the rider by one tick.

        Handles idle-to-picking-up activation, movement along the planned
        path using up to ``speed`` units, arrival at the restaurant, and
        delivery to the customer. A rider waits when a lower-id rider blocks
        its next waypoint, up to ``stall_limit`` ticks, to avoid deadlock.
        """
        if self.state == STATE_IDLE:
            if not self.orders:
                self.special_case = False
                return
            self._activate_order()

        budget = self.speed
        while budget > 0 and self.orders and self.state != STATE_IDLE:
            if self.path:
                if self._is_blocked():
                    break
                budget = self._step(budget)
            elif self.state == STATE_PICKING_UP:
                self._arrive_at_merchant()
            else:
                self._complete_delivery()

    def to_dict(self) -> Dict[str, Any]:
        """Return a JSON-serialisable snapshot of the rider."""
        return {
            "rider_id": self.rider_id,
            "x": self.x,
            "y": self.y,
            "speed": self.speed,
            "state": self.state,
            "order_ids": [order.id for order in self.orders],
            "special_case": self.special_case,
            "log": list(self.log),
        }

    # ------------------------------------------------------------------
    # State transitions
    # ------------------------------------------------------------------
    def _activate_order(self) -> None:
        """Start picking up the first queued order (idle -> picking up)."""
        order = self.orders[0]
        self.state = STATE_PICKING_UP
        order.status = STATUS_PICKING_UP
        self._set_path(order.res_center)
        self._record(EVENT_ACCEPTED, order.id)

    def _arrive_at_merchant(self) -> None:
        """Handle arrival at the restaurant (picking up -> delivering)."""
        order = self.orders[0]
        self.state = STATE_DELIVERING
        order.status = STATUS_DELIVERING
        self._record(EVENT_ARRIVED, order.id)
        self._set_path(order.cus_center)

    def _complete_delivery(self) -> None:
        """Finish the current order and release the rider.

        Completes the order, records the delivery, credits the delivery fee
        to system funds, and either becomes idle or starts the next order.
        """
        order = self.orders.pop(0)
        order.complete(int(get_value("current_tick", 0)))
        self._record(EVENT_DELIVERED, order.id)
        fee = int(get_value("delivery_fee", 100))
        set_value("funds", int(get_value("funds", 0)) + fee)
        self.path = []
        self.stall_count = 0
        self.special_case = False
        self.state = STATE_IDLE
        if self.orders:
            self._activate_order()

    # ------------------------------------------------------------------
    # Movement helpers
    # ------------------------------------------------------------------
    def _set_path(self, target: Tuple[int, int]) -> None:
        """Plan a path to ``target`` and update the special-case flag.

        ``special_case`` is True when the target is directly above/below
        (same x) or directly beside (same y) the rider, i.e. a straight run.

        Args:
            target: Destination cell centre.
        """
        self.path = self._planner.plan((self.x, self.y), target)
        self.stall_count = 0
        self.special_case = bool(self.path) and (
            self.x == target[0] or self.y == target[1]
        )

    def _is_blocked(self) -> bool:
        """Return True if this rider should yield the next waypoint.

        A rider yields to a lower-id rider standing on its next waypoint.
        After ``stall_limit`` waiting ticks it proceeds anyway, which
        prevents indefinite deadlock.

        Returns:
            Whether movement should pause this tick.
        """
        if not self.path:
            return False
        wx, wy = self.path[0]
        limit = int(get_value("stall_limit", 3))
        for other in get_value("riders") or []:
            if other is self:
                continue
            if other.x == wx and other.y == wy and other.rider_id < self.rider_id:
                if self.stall_count < limit:
                    self.stall_count += 1
                    return True
                self.stall_count = 0
                return False
        self.stall_count = 0
        return False

    def _step(self, budget: int) -> int:
        """Move toward the next waypoint using at most ``budget`` units.

        Args:
            budget: Remaining movement units for this tick.

        Returns:
            Movement units left unused after this step.
        """
        tx, ty = self.path[0]
        dx = tx - self.x
        dy = ty - self.y
        remaining = budget
        move_x = min(remaining, abs(dx))
        self.x += move_x * _sign(dx)
        remaining -= move_x
        move_y = min(remaining, abs(dy))
        self.y += move_y * _sign(dy)
        remaining -= move_y
        if (self.x, self.y) == (tx, ty):
            self.path.pop(0)
        return remaining
