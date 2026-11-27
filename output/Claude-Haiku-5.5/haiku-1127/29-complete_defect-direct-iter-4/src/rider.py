"""Rider model: state machine, grid movement and event logging.

Rider states:
    0 = idle, 1 = picking up (en route to restaurant),
    2 = delivering (en route to customer).

Events written to ``rider.log`` (dicts with "event" and "order_id"):
    "spawn", "accepted_order", "arrived_at_merchant", "delivered_to_customer".
Detailed records (time, position, state) are kept in ``rider.history``.
"""

import logging
from typing import Any, Dict, List, Optional, Tuple

import globalvar
from path_planner import PathPlanner, Point

logger = logging.getLogger(__name__)

STATE_IDLE = 0
STATE_PICKING_UP = 1
STATE_DELIVERING = 2
STATE_NAMES = {
    STATE_IDLE: "idle",
    STATE_PICKING_UP: "picking up",
    STATE_DELIVERING: "delivering",
}
DEFAULT_SPEED = 50

_planner = PathPlanner()


def _config_value(key: str, default: Any) -> Any:
    """Read a configuration value from the global store."""
    config = globalvar.get_value("config") or {}
    return config.get(key, default)


def _sign(value: int) -> int:
    """Return -1, 0 or 1 according to the sign of ``value``."""
    return (value > 0) - (value < 0)


def _add_funds(amount: int) -> None:
    """Add ``amount`` to the system fund balance."""
    globalvar.set_value("funds", (globalvar.get_value("funds") or 0) + amount)


class Rider:
    """A delivery rider that moves along streets and serves orders in a queue."""

    def __init__(self, rider_id: int, x: int = 0, y: int = 0,
                 speed: Optional[int] = None) -> None:
        """Create a rider and log its spawn event.

        Args:
            rider_id: Unique identifier of the rider.
            x: Initial x coordinate (0-800).
            y: Initial y coordinate (0-800).
            speed: Movement speed in units per tick. Defaults to the
                configured ``rider_speed``.

        Raises:
            ValueError: If the speed is not positive.
        """
        if speed is None:
            speed = int(_config_value("rider_speed", DEFAULT_SPEED))
        if int(speed) <= 0:
            raise ValueError("Rider speed must be positive")
        self.rider_id: int = int(rider_id)
        self.x: int = int(x)
        self.y: int = int(y)
        self.speed: int = int(speed)
        self.state: int = STATE_IDLE
        self.orders: List[Any] = []
        self.special_case: bool = False
        self.route: List[Point] = []
        self._straight = False
        self._waiting = False
        self.log: List[Dict[str, Any]] = []
        self.history: List[Dict[str, Any]] = []
        self._record("spawn", None)

    @property
    def position(self) -> Point:
        """Current (x, y) position."""
        return (self.x, self.y)

    @property
    def state_name(self) -> str:
        """Human readable state label."""
        return STATE_NAMES.get(self.state, "unknown")

    def sync_state(self) -> None:
        """Accept the next queued order if the rider is idle.

        Transition: Idle (0) -> Picking Up (1) when an order is assigned.
        The route to the restaurant is planned and "accepted_order" logged.
        """
        if self.state != STATE_IDLE or not self.orders:
            return
        order = self.orders[0]
        self.state = STATE_PICKING_UP
        self._set_route(order.res_pos)
        self._record("accepted_order", order.id)

    def move(self) -> None:
        """Advance the rider by one tick.

        Moves up to ``speed`` units along the planned route, then processes
        arrivals (pickup at the restaurant, delivery at the customer) that
        happen during this tick. Multi-destination routing re-plans the
        restaurant-to-customer leg immediately upon pickup.
        """
        self.sync_state()
        if self.state == STATE_IDLE:
            return
        if self.route:
            self._advance()
        safety = 2 * len(self.orders) + 4
        while self.state != STATE_IDLE and not self.route and safety > 0:
            self._on_arrival()
            safety -= 1

    def replan(self) -> None:
        """Recompute the current route (used for error recovery)."""
        self._waiting = False
        if self.state == STATE_IDLE or not self.orders:
            self.route = []
            self._straight = False
        elif self.state == STATE_PICKING_UP:
            self._set_route(self.orders[0].res_pos)
        else:
            self._set_route(self.orders[0].cus_pos)
        self._update_special()

    def _set_route(self, goal: Point) -> None:
        """Plan a route from the current position to ``goal``."""
        points = _planner.plan(self.position, goal)
        self.route = points[1:]
        self._straight = PathPlanner.is_straight(points)
        self._update_special()

    def _update_special(self) -> None:
        """Refresh the special_case flag (straight approach or waiting)."""
        self.special_case = self._straight or self._waiting

    def _advance(self) -> None:
        """Consume the movement budget of this tick along the route.

        Conflict avoidance: a rider waits when the next waypoint is occupied
        by a moving rider with a lower id. Priority is ordered by id, so the
        waiting relation is acyclic and cannot deadlock.
        """
        remaining = self.speed
        self._waiting = False
        while remaining > 0 and self.route:
            tx, ty = self.route[0]
            if (tx, ty) == self.position:
                self.route.pop(0)
                continue
            if self._is_blocked(tx, ty):
                self._waiting = True
                break
            dx = tx - self.x
            dy = ty - self.y
            move_x = min(abs(dx), remaining)
            self.x += _sign(dx) * move_x
            remaining -= move_x
            move_y = min(abs(dy), remaining)
            self.y += _sign(dy) * move_y
            remaining -= move_y
            if (self.x, self.y) == (tx, ty):
                self.route.pop(0)
        self._update_special()

    def _is_blocked(self, tx: int, ty: int) -> bool:
        """Return True if a higher-priority moving rider occupies (tx, ty)."""
        for other in globalvar.get_value("riders") or []:
            if other is self:
                continue
            if (other.rider_id < self.rider_id
                    and other.state != STATE_IDLE
                    and other.position == (tx, ty)):
                return True
        return False

    def _on_arrival(self) -> None:
        """Handle arrival at the current destination and change state."""
        if not self.orders:
            self.state = STATE_IDLE
            self.route = []
            return
        order = self.orders[0]
        if self.state == STATE_PICKING_UP:
            order.mark_picked_up(self._now())
            self._record("arrived_at_merchant", order.id)
            self.state = STATE_DELIVERING
            self._set_route(order.cus_pos)
        elif self.state == STATE_DELIVERING:
            reward = order.complete(self._now())
            self._record("delivered_to_customer", order.id)
            self.orders.pop(0)
            _add_funds(reward)
            self.state = STATE_IDLE
            self.route = []
            self.sync_state()

    def _now(self) -> int:
        """Return the current simulated tick."""
        return int(globalvar.get_value("time", 0) or 0)

    def _record(self, event: str, order_id: Optional[int]) -> None:
        """Append an event to ``log`` and a detailed record to ``history``."""
        self.log.append({"event": event, "order_id": order_id})
        self.history.append({
            "time": self._now(),
            "rider_id": self.rider_id,
            "event": event,
            "order_id": order_id,
            "x": self.x,
            "y": self.y,
            "state": self.state,
        })

    def to_dict(self) -> Dict[str, Any]:
        """Return a JSON-serialisable description of the rider."""
        return {
            "rider_id": self.rider_id,
            "x": self.x,
            "y": self.y,
            "speed": self.speed,
            "state": self.state,
            "orders": [order.id for order in self.orders],
            "special_case": self.special_case,
        }
