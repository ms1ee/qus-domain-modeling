"""Rider model: state machine, movement and order execution."""

import logging
from typing import Any, Dict, List, Optional, Tuple

import globalvar
from path_planner import PathPlanner

logger = logging.getLogger(__name__)

# Rider state enumeration
IDLE = 0
PICKING_UP = 1
DELIVERING = 2
STATE_NAMES = {IDLE: "idle", PICKING_UP: "picking up", DELIVERING: "delivering"}

# Movement speed in units per tick (PRD section 2.2).
# Note: section 2.1 lists 10 for newly recruited riders; the 20 units/tick
# value from section 2.2 is used for all riders here.
RIDER_SPEED = 20
SPAWN_X = 400
SPAWN_Y = 400

_planner = PathPlanner()


def _now() -> int:
    """Return the current simulated tick."""
    return int(globalvar.get_value("current_time", 0) or 0)


class Rider:
    """A delivery rider that picks up and delivers orders on the street grid.

    An order is assigned by appending it to ``rider.orders`` with status
    ``"assigned"``. ``move()`` then performs all state transitions:

    * Idle (0) -> Picking up (1) when an assigned order is started.
    * Picking up (1) -> Delivering (2) on arrival at the restaurant.
    * Delivering (2) -> Idle (0) on delivery to the customer.
    """

    def __init__(self, rider_id: int) -> None:
        """Create a rider at the spawn point (400, 400) in the idle state.

        Args:
            rider_id: Unique identifier assigned by the system.
        """
        self.rider_id: int = rider_id
        self.x: int = SPAWN_X
        self.y: int = SPAWN_Y
        self.speed: int = RIDER_SPEED
        self.state: int = IDLE
        self.orders: List[Any] = []
        self.special_case: bool = False
        self.current_order: Optional[Any] = None
        self.path: List[Tuple[int, int]] = []
        self.log: List[Dict[str, Any]] = []
        self._record("spawn", None)

    @property
    def state_name(self) -> str:
        """Human-readable name of the current state."""
        return STATE_NAMES.get(self.state, "unknown")

    @property
    def position(self) -> Tuple[int, int]:
        """Current (x, y) location."""
        return (self.x, self.y)

    def active_order_count(self) -> int:
        """Number of assigned orders that are not yet completed."""
        return sum(1 for o in self.orders if o.status != "completed")

    def is_idle(self) -> bool:
        """Return True when the rider is idle and has no queued order."""
        return self.state == IDLE and not any(o.status == "assigned" for o in self.orders)

    def _record(self, event: str, order_id: Optional[int]) -> None:
        """Append a status-change entry to the rider log."""
        entry = {
            "event": event,
            "order_id": order_id,
            "time": _now(),
            "x": self.x,
            "y": self.y,
            "state": self.state,
        }
        self.log.append(entry)
        logger.info(
            "rider %d event=%s order=%s t=%d pos=(%d,%d)",
            self.rider_id, event, order_id, entry["time"], self.x, self.y,
        )

    def _next_assigned_order(self) -> Optional[Any]:
        """Return the earliest assigned-but-not-started order, if any."""
        for order in self.orders:
            if order.status == "assigned":
                return order
        return None

    def _start_order(self, order: Any) -> None:
        """Begin the pickup leg of an order (Idle -> Picking up)."""
        here = self.position
        self.current_order = order
        order.status = "picking_up"
        self.state = PICKING_UP
        self.path = _planner.plan(here, order.restaurant_pos)
        self.special_case = _planner.is_straight(here, order.restaurant_pos)
        self._record("accepted_order", order.id)

    def _advance(self) -> None:
        """Move along ``self.path`` by up to ``self.speed`` units this tick."""
        budget = self.speed
        while budget > 0 and self.path:
            tx, ty = self.path[0]
            dx = tx - self.x
            dy = ty - self.y
            dist = abs(dx) + abs(dy)
            if dist <= budget:
                self.x, self.y = tx, ty
                budget -= dist
                self.path.pop(0)
            else:
                step_x = min(abs(dx), budget)
                self.x += step_x if dx > 0 else -step_x
                budget -= step_x
                step_y = min(abs(dy), budget)
                self.y += step_y if dy > 0 else -step_y
                budget -= step_y
                break

    def _check_arrival(self) -> None:
        """Perform state transitions when the current leg has been completed."""
        while not self.path and self.current_order is not None:
            order = self.current_order
            here = self.position
            if self.state == PICKING_UP and here == order.restaurant_pos:
                self.state = DELIVERING
                order.status = "delivering"
                self._record("arrived_at_merchant", order.id)
                self.path = _planner.plan(here, order.customer_pos)
                self.special_case = _planner.is_straight(here, order.customer_pos)
            elif self.state == DELIVERING and here == order.customer_pos:
                order.complete(_now())
                self._record("delivered_to_customer", order.id)
                self.state = IDLE
                self.current_order = None
                self.special_case = False
            else:
                break

    def move(self) -> None:
        """Advance the rider by one tick.

        Starts the next assigned order when idle, moves along the planned
        street route, and applies arrival and delivery state transitions.
        """
        if self.state == IDLE:
            order = self._next_assigned_order()
            if order is None:
                return
            self._start_order(order)
        if self.current_order is None:
            return
        self._advance()
        self._check_arrival()

    def to_dict(self) -> Dict[str, Any]:
        """Return a JSON-serialisable snapshot of the rider."""
        return {
            "rider_id": self.rider_id,
            "x": self.x,
            "y": self.y,
            "speed": self.speed,
            "state": self.state,
            "special_case": self.special_case,
            "orders": [o.id for o in self.orders],
            "log": list(self.log),
        }
