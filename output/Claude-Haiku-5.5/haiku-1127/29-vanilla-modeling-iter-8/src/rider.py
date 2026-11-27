"""Rider model: movement, state machine and order lifecycle.

State machine:
    0 (idle)        -> 1 (picking up)  when an order is present in ``orders``
    1 (picking up)  -> 2 (delivering)  on arrival at the restaurant
    2 (delivering)  -> 0 (idle)        on delivery; the order is removed
"""

import logging
from typing import Any, Dict, List, Optional, Tuple

from globalvar import get_value
from path_planner import PathPlanner

logger = logging.getLogger(__name__)

STATE_IDLE = 0
STATE_PICKING_UP = 1
STATE_DELIVERING = 2

INITIAL_X = 435
INITIAL_Y = 385
INITIAL_SPEED = 10

Point = Tuple[int, int]


class Rider:
    """A delivery rider that moves on the grid and serves orders.

    Attributes:
        rider_id: Unique identifier.
        x, y: Current coordinates.
        speed: Distance covered per tick.
        state: 0 idle, 1 picking up, 2 delivering.
        orders: Assigned orders; ``orders[0]`` is the one being served.
        special_case: True while the rider is aligned with its target on
            one axis (directly above/below or beside it).
        path: Remaining waypoints of the current leg.
        log: Chronological list of event dictionaries. Each entry has the
            keys "event" and "order_id" plus "time", "x", "y", "state".
    """

    def __init__(self, rider_id: int) -> None:
        """Create an idle rider at the default depot position.

        Args:
            rider_id: Unique identifier assigned by the system.
        """
        self.rider_id: int = rider_id
        self.x: int = INITIAL_X
        self.y: int = INITIAL_Y
        self.speed: int = INITIAL_SPEED
        self.state: int = STATE_IDLE
        self.orders: List[Any] = []
        self.special_case: bool = False
        self.path: List[Point] = []
        self.log: List[Dict[str, Any]] = []
        self._record("spawn", None)

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------
    @property
    def position(self) -> Point:
        """Current (x, y) position."""
        return (self.x, self.y)

    def current_order(self) -> Optional[Any]:
        """Return the order currently being served, or None."""
        return self.orders[0] if self.orders else None

    def current_target(self) -> Optional[Point]:
        """Return the active destination for the current state."""
        order = self.current_order()
        if order is None:
            return None
        if self.state == STATE_DELIVERING:
            return order.customer_pos
        return order.restaurant_pos

    def _now(self) -> int:
        return int(get_value("tick", 0) or 0)

    def _record(self, event: str, order_id: Optional[int]) -> None:
        """Append an event to the rider's log."""
        self.log.append(
            {
                "event": event,
                "order_id": order_id,
                "time": self._now(),
                "x": self.x,
                "y": self.y,
                "state": self.state,
                "rider_id": self.rider_id,
            }
        )

    def _is_aligned(self, target: Point) -> bool:
        """True if the rider shares a row or column with the target."""
        return self.position != target and (
            self.x == target[0] or self.y == target[1]
        )

    def _advance(self, budget: int) -> None:
        """Consume up to ``budget`` distance along the planned path.

        Segments are axis-aligned, so each tick moves the rider along a
        single street direction (horizontal or vertical).
        """
        while budget > 0 and self.path:
            wx, wy = self.path[0]
            dx = wx - self.x
            dy = wy - self.y
            dist = abs(dx) + abs(dy)
            if dist <= budget:
                self.x, self.y = wx, wy
                self.path.pop(0)
                budget -= dist
            else:
                if dx != 0:
                    self.x += budget if dx > 0 else -budget
                else:
                    self.y += budget if dy > 0 else -budget
                budget = 0

    def _arrive(self, order: Any) -> None:
        """Handle arrival at the current destination and transition state."""
        if self.state == STATE_PICKING_UP:
            self.state = STATE_DELIVERING
            self.path = []
            self._record("arrived_at_merchant", order.id)
            logger.info("Rider %s arrived at restaurant for order %s",
                        self.rider_id, order.id)
        elif self.state == STATE_DELIVERING:
            order.complete(self._now())
            self.orders.remove(order)
            self.state = STATE_IDLE
            self.path = []
            self.special_case = False
            self._record("delivered_to_customer", order.id)
            logger.info("Rider %s delivered order %s", self.rider_id, order.id)

    # ------------------------------------------------------------------
    # Public behaviour
    # ------------------------------------------------------------------
    def move(self) -> None:
        """Advance the rider by one tick.

        Performs any state transition triggered by the current conditions
        (accepting a new order, arriving at a destination) and moves the
        rider up to ``speed`` units along the street grid.
        """
        order = self.current_order()

        if self.state == STATE_IDLE:
            if order is None:
                return
            self.state = STATE_PICKING_UP
            self.path = []
            self._record("accepted_order", order.id)

        if order is None:
            logger.warning("Rider %s had an active state without orders; "
                           "resetting to idle", self.rider_id)
            self.state = STATE_IDLE
            self.path = []
            self.special_case = False
            return

        target = self.current_target()
        if target is None:
            return

        if not self.path and self.position != target:
            self.path = PathPlanner.plan_path(self.position, target)

        self.special_case = self._is_aligned(target)
        self._advance(self.speed)

        if self.position == target and not self.path:
            self._arrive(order)

    def to_dict(self) -> Dict[str, Any]:
        """Return a JSON-serialisable snapshot of the rider."""
        return {
            "rider_id": self.rider_id,
            "x": self.x,
            "y": self.y,
            "speed": self.speed,
            "state": self.state,
            "special_case": self.special_case,
            "orders": [order.id for order in self.orders],
            "log": list(self.log),
        }

    def __repr__(self) -> str:
        return (f"Rider(id={self.rider_id}, pos=({self.x}, {self.y}), "
                f"state={self.state}, orders={len(self.orders)})")
