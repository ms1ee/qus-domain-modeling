"""Rider model: state machine, movement and delivery event log.

Rider states:
    0 = Idle, 1 = Picking Up (heading to restaurant),
    2 = Delivering (heading to customer).

Events written to ``Rider.log``:
    "spawn", "accepted_order", "arrived_at_merchant", "delivered_to_customer".
"""

import logging

from globalvar import get_value
from grid import DEFAULT_RIDER_SPEED, RIDER_SPAWN
from path_planner import PathPlanner

logger = logging.getLogger("dispatch.rider")

IDLE = 0
PICKING_UP = 1
DELIVERING = 2

STATE_NAMES = {
    IDLE: "Idle",
    PICKING_UP: "Picking Up",
    DELIVERING: "Delivering",
}

_planner = PathPlanner()


class Rider:
    """A delivery rider that moves on the grid and serves assigned orders."""

    def __init__(self, rider_id: int) -> None:
        """Create a rider at the spawn point, idle, with a spawn log entry.

        Args:
            rider_id: Unique integer identifier of the rider.
        """
        self.rider_id = rider_id
        self.x, self.y = RIDER_SPAWN
        self.speed = int(get_value("rider_speed", DEFAULT_RIDER_SPEED))
        self.state = IDLE
        self.orders = []
        self.special_case = False
        self.log = []
        self.path = []
        self.distance_travelled = 0
        self._target = None
        self._record("spawn", None)

    @property
    def position(self) -> tuple:
        """Current (x, y) position."""
        return (self.x, self.y)

    @property
    def state_name(self) -> str:
        """Human readable state name."""
        return STATE_NAMES.get(self.state, "Unknown")

    def is_idle(self) -> bool:
        """Return True if the rider is free to take a new order."""
        return self.state == IDLE and not self.orders

    def reset_movement(self) -> None:
        """Clear the planned path (used for error recovery)."""
        self.path = []
        self._target = None

    def move(self) -> None:
        """Advance the rider by one tick (one call = one unit of time).

        Handles the idle->picking-up transition when an order is present,
        moves along the planned route by up to ``speed`` units, and applies
        the arrival transitions at the restaurant and the customer.
        """
        if self.state == IDLE:
            if not self.orders:
                return
            self.state = PICKING_UP
            self.reset_movement()
            order = self.orders[0]
            order.status = "picking_up"
            self._record("accepted_order", order.id)

        target = self._current_target()
        if target is None:
            logger.warning("Rider %s has no target; resetting to idle",
                           self.rider_id)
            self.state = IDLE
            self.reset_movement()
            return

        if self._target != target:
            self._target = target
            self.path = _planner.plan(self.position, target)
            self.special_case = self.x == target[0] or self.y == target[1]

        self._advance()
        if self.position == target:
            self._on_arrival()

    def _current_order(self):
        """Return the order currently being served, or None."""
        return self.orders[0] if self.orders else None

    def _current_target(self):
        """Return the coordinate the rider is heading to, or None."""
        order = self._current_order()
        if order is None:
            return None
        if self.state == PICKING_UP:
            return order.res_pos
        if self.state == DELIVERING:
            return order.cus_pos
        return None

    def _advance(self) -> None:
        """Move along the planned waypoints by at most ``speed`` units."""
        remaining = self.speed
        while remaining > 0 and self.path:
            wx, wy = self.path[0]
            dx = wx - self.x
            dy = wy - self.y
            if dx == 0 and dy == 0:
                self.path.pop(0)
                continue
            if dx != 0:
                step = min(remaining, abs(dx))
                self.x += step if dx > 0 else -step
            else:
                step = min(remaining, abs(dy))
                self.y += step if dy > 0 else -step
            remaining -= step
            self.distance_travelled += step
            if (self.x, self.y) == (wx, wy):
                self.path.pop(0)

    def _on_arrival(self) -> None:
        """Apply state transitions when the rider reaches its target."""
        order = self._current_order()
        if order is None:
            self.state = IDLE
            self.reset_movement()
            return
        if self.state == PICKING_UP:
            self.state = DELIVERING
            order.status = "delivering"
            self.reset_movement()
            self._record("arrived_at_merchant", order.id)
        elif self.state == DELIVERING:
            self.orders.pop(0)
            order.complete(self._now())
            self.state = IDLE
            self.reset_movement()
            self._record("delivered_to_customer", order.id)

    def _now(self) -> int:
        """Return the current simulated tick."""
        return int(get_value("tick", 0))

    def _record(self, event: str, order_id) -> None:
        """Append a status-change entry to the rider's log."""
        self.log.append({
            "time": self._now(),
            "event": event,
            "order_id": order_id,
            "rider_id": self.rider_id,
            "x": self.x,
            "y": self.y,
            "state": self.state,
        })
