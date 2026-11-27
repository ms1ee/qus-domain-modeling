"""Rider model: state machine, street-following movement and event log.

Rider states:
    0 idle, 1 picking up (en route to restaurant), 2 delivering (en route to customer).

State transitions:
    idle -> picking up        when an assigned order is accepted (inside move()).
    picking up -> delivering  on arrival at the restaurant.
    delivering -> picking up  after completing an order while more orders are queued.
    delivering -> idle        after completing the last active order.
"""

import logging
from typing import Any, Dict, List, Optional

import globalvar
from order_model import (
    STATUS_ASSIGNED,
    STATUS_COMPLETED,
)
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
DEFAULT_SPEED = 20
MAX_WAIT_TICKS = 3


class Rider:
    """A delivery rider that moves along streets and serves orders.

    Attributes:
        rider_id: Unique identifier.
        x, y: Current coordinates.
        speed: Distance units travelled per tick.
        state: 0 idle, 1 picking up, 2 delivering.
        orders: All orders assigned to this rider, including completed history.
        special_case: Flag raised for special path situations (off-street
            targets, aligned targets, or waiting on another rider).
        log: Chronological list of status-change entries. Each entry is a dict
            with keys ``event``, ``order_id``, ``time``, ``rider_id``, ``x``,
            ``y`` and ``state``.
    """

    def __init__(self, rider_id: int, x: int = 400, y: int = 400,
                 speed: int = DEFAULT_SPEED) -> None:
        """Create a rider and log its spawn.

        Args:
            rider_id: Unique identifier.
            x: Initial x coordinate.
            y: Initial y coordinate.
            speed: Movement speed in units per tick.
        """
        self.rider_id: int = int(rider_id)
        self.x: int = int(x)
        self.y: int = int(y)
        self.speed: int = int(speed)
        self.state: int = STATE_IDLE
        self.orders: List[Any] = []
        self.special_case: bool = False
        self.log: List[Dict[str, Any]] = []
        self._planner = PathPlanner()
        self._path: List[Point] = []
        self._current_order: Optional[Any] = None
        self._wait_ticks: int = 0
        self._record("spawn", None)

    # ------------------------------------------------------------------
    # Properties and queries
    # ------------------------------------------------------------------
    @property
    def position(self) -> Point:
        """Current ``(x, y)`` position."""
        return (self.x, self.y)

    @property
    def state_name(self) -> str:
        """Human-readable name of the current state."""
        return STATE_NAMES.get(self.state, "unknown")

    def active_orders(self) -> List[Any]:
        """Return orders that are not yet completed."""
        return [order for order in self.orders if order.status != STATUS_COMPLETED]

    @property
    def route_waypoints(self) -> List[Point]:
        """Remaining waypoints of the current leg (copy)."""
        return list(self._path)

    # ------------------------------------------------------------------
    # Simulation
    # ------------------------------------------------------------------
    def move(self) -> None:
        """Advance the rider by one tick.

        Accepts a new order if idle, moves up to ``speed`` units along the
        street path, and performs state transitions on arrival.
        """
        if self.state == STATE_IDLE:
            nxt = self._next_order()
            if nxt is None:
                return
            self._accept(nxt)

        budget = self.speed
        while True:
            if not self._path:
                if not self._on_leg_finished():
                    break
                continue
            if budget <= 0:
                break
            budget = self._advance(budget)

    def recover(self) -> None:
        """Reset movement state after an unexpected error.

        Clears the path, returns the rider to idle and re-queues any
        in-progress orders so they are restarted cleanly.
        """
        self._path = []
        self._current_order = None
        self._wait_ticks = 0
        self.special_case = False
        for order in self.active_orders():
            order.status = STATUS_ASSIGNED
        self.state = STATE_IDLE
        self._record("recovered", None)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------
    def _next_order(self) -> Optional[Any]:
        """Return the first queued order that has not been accepted yet."""
        for order in self.orders:
            if order.status == STATUS_ASSIGNED:
                return order
        return None

    def _accept(self, order: Any) -> None:
        """Start working on ``order``: move towards the restaurant."""
        self._current_order = order
        order.mark_picking_up()
        self.state = STATE_PICKING_UP
        self._record("accepted_order", order.id)
        self._set_path(order.res_pos)

    def _set_path(self, goal: Point) -> None:
        """Plan the route from the current position to ``goal``."""
        self._path = self._planner.plan(self.position, goal)
        self.special_case = self._planner.is_special_case(self.position, goal)

    def _on_leg_finished(self) -> bool:
        """Handle arrival at the current leg destination.

        Returns:
            True if the rider should continue processing in this tick,
            False if it has nothing more to do.
        """
        order = self._current_order
        if order is None:
            return False
        tick = int(globalvar.get_value("tick", 0))

        if self.state == STATE_PICKING_UP:
            order.mark_delivering(tick)
            self.state = STATE_DELIVERING
            self._record("arrived_at_merchant", order.id)
            self._set_path(order.cus_pos)
            return True

        if self.state == STATE_DELIVERING:
            order.mark_completed(tick)
            self._record("delivered_to_customer", order.id)
            self._current_order = None
            nxt = self._next_order()
            if nxt is None:
                self.state = STATE_IDLE
                self.special_case = False
                return False
            self._accept(nxt)
            return True

        return False

    def _advance(self, budget: int) -> int:
        """Move towards the next waypoint using up to ``budget`` units.

        Returns:
            Remaining budget for this tick.
        """
        target = self._path[0]
        dx = target[0] - self.x
        dy = target[1] - self.y
        dist = abs(dx) + abs(dy)

        if dist == 0:
            self._path.pop(0)
            return budget

        if dist > budget:
            step_x = min(budget, abs(dx))
            if step_x:
                self.x += step_x if dx > 0 else -step_x
            remaining = budget - step_x
            step_y = min(remaining, abs(dy))
            if step_y:
                self.y += step_y if dy > 0 else -step_y
            return 0

        # Conflict avoidance: wait briefly if another moving rider occupies
        # the waypoint. After MAX_WAIT_TICKS the rider proceeds anyway, which
        # breaks potential deadlocks.
        if self._is_blocked(target) and self._wait_ticks < MAX_WAIT_TICKS:
            self._wait_ticks += 1
            self.special_case = True
            return 0

        self._wait_ticks = 0
        self.x, self.y = target
        self._path.pop(0)
        return budget - dist

    def _is_blocked(self, point: Point) -> bool:
        """Return True if another active rider occupies ``point``."""
        for other in globalvar.get_value("riders", []) or []:
            if other is self:
                continue
            if other.state != STATE_IDLE and other.position == point:
                return True
        return False

    def _record(self, event: str, order_id: Optional[int]) -> None:
        """Append a status-change entry to the rider log."""
        entry = {
            "event": event,
            "order_id": order_id,
            "time": int(globalvar.get_value("tick", 0)),
            "rider_id": self.rider_id,
            "x": self.x,
            "y": self.y,
            "state": self.state,
        }
        self.log.append(entry)
        logger.debug("Rider %s: %s (order=%s) at (%s,%s)",
                     self.rider_id, event, order_id, self.x, self.y)

    def __repr__(self) -> str:
        return (f"Rider(id={self.rider_id}, pos=({self.x},{self.y}), "
                f"state={self.state_name}, orders={len(self.orders)})")
