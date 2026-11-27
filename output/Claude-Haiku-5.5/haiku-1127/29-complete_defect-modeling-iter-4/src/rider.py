"""Rider model: state machine, movement along planned routes and event logs.

State machine:
    IDLE (0)        -> PICKING_UP (1)  when an order is accepted (queued order exists)
    PICKING_UP (1)  -> DELIVERING (2)  when the restaurant is reached
    DELIVERING (2)  -> IDLE (0)        when the customer is reached (or the next
                                       queued order is accepted immediately)
"""

import logging
from typing import Any, Dict, List, Optional, Tuple

from globalvar import get_value
from grid import GridMap
from path_planner import PathNotFoundError, PathPlanner

logger = logging.getLogger(__name__)

IDLE = 0
PICKING_UP = 1
DELIVERING = 2
STATE_NAMES = {IDLE: "idle", PICKING_UP: "picking up", DELIVERING: "delivering"}

SPAWN_POINT = (400, 400)  # central street intersection
DEFAULT_SPEED = 50
MAX_WAIT_TICKS = 3        # yield limit before deadlock avoidance forces progress
MAX_LOG_ENTRIES = 5000    # bounds memory use during long runs

Point = Tuple[int, int]

_fallback_planner: Optional[PathPlanner] = None


def _configured_speed() -> int:
    """Return the default rider speed from the system configuration."""
    config = get_value("config")
    return int(config.default_rider_speed) if config is not None else DEFAULT_SPEED


def _planner() -> PathPlanner:
    """Return the shared path planner, creating a fallback if needed."""
    global _fallback_planner
    planner = get_value("path_planner")
    if planner is None:
        if _fallback_planner is None:
            _fallback_planner = PathPlanner(GridMap())
        planner = _fallback_planner
    return planner


class Rider:
    """A delivery rider that moves on the grid and serves assigned orders.

    Attributes:
        rider_id: Unique identifier.
        x, y: Current coordinates.
        speed: Movement speed in units per tick.
        state: 0 = idle, 1 = picking up, 2 = delivering.
        orders: Assigned orders; the first one is the current order.
        special_case: True when the current approach is a driveway
            (target directly above or below the rider's route).
        log: Event dictionaries with keys "event" and "order_id" (plus "time",
            "x" and "y").
    """

    def __init__(self, rider_id: int) -> None:
        """Create an idle rider at the spawn point.

        Args:
            rider_id: Unique identifier of the rider.
        """
        self.rider_id: int = int(rider_id)
        self.x: int = SPAWN_POINT[0]
        self.y: int = SPAWN_POINT[1]
        self.speed: int = _configured_speed()
        self.state: int = IDLE
        self.special_case: bool = False
        self.orders: List[Any] = []
        self.target: Optional[Point] = None
        self.path: List[Point] = []
        self.wait_ticks: int = 0
        self.log: List[Dict[str, Any]] = []
        self._record("spawn", None)

    # ------------------------------------------------------------------
    # properties and helpers
    # ------------------------------------------------------------------
    @property
    def position(self) -> Point:
        """Current coordinates as a tuple."""
        return (self.x, self.y)

    @property
    def current_order(self) -> Any:
        """The order being served, or None when no orders are assigned."""
        return self.orders[0] if self.orders else None

    @property
    def state_name(self) -> str:
        """Human-readable state name."""
        return STATE_NAMES.get(self.state, "unknown")

    def _now(self) -> int:
        """Return the current simulated tick."""
        return int(get_value("simulated_time", 0) or 0)

    def _record(self, event: str, order_id: Optional[int]) -> None:
        """Append an event to the rider log, trimming old entries if needed."""
        self.log.append({
            "event": event,
            "order_id": order_id,
            "time": self._now(),
            "x": self.x,
            "y": self.y,
        })
        if len(self.log) > MAX_LOG_ENTRIES:
            del self.log[: len(self.log) - MAX_LOG_ENTRIES]
        logger.info("Rider %d: %s (order %s) at (%d,%d)",
                    self.rider_id, event, order_id, self.x, self.y)

    def reset_after_error(self) -> None:
        """Return the rider to a consistent idle state after an internal error.

        Assigned orders are kept so that they are re-accepted on the next tick.
        """
        self.state = IDLE
        self.target = None
        self.path = []
        self.special_case = False
        self.wait_ticks = 0

    def to_dict(self) -> Dict[str, Any]:
        """Return a JSON-serialisable representation of the rider."""
        return {
            "rider_id": self.rider_id,
            "x": self.x,
            "y": self.y,
            "speed": self.speed,
            "state": self.state,
            "special_case": self.special_case,
            "orders": [getattr(order, "id", None) for order in self.orders],
        }

    # ------------------------------------------------------------------
    # main tick logic
    # ------------------------------------------------------------------
    def move(self) -> None:
        """Advance the rider by one tick.

        Handles order acceptance, movement along the route, arrival at the
        restaurant and delivery to the customer, including all state
        transitions and their log entries.
        """
        now = self._now()
        if self.state == IDLE:
            if not self.orders:
                return
            self._accept_order(now)
        if self.state == IDLE or self.target is None:
            return
        self._advance(now)
        self._handle_arrivals(now)

    def _accept_order(self, now: int) -> None:
        """Start the pickup leg for the first queued order."""
        order = self.orders[0]
        order.status = "picking_up"
        self.state = PICKING_UP
        self._record("accepted_order", order.id)
        self._plan_to(order.restaurant_pos, order)

    def _plan_to(self, target: Point, order: Any) -> None:
        """Plan a route from the current position to ``target``."""
        try:
            route = _planner().plan(self.position, target, self.speed)
            self.path = list(route.points[1:])
            self.special_case = route.has_driveway
            order.add_distance(route.total_distance)
        except PathNotFoundError as exc:
            logger.error("Rider %d: %s; snapping to target", self.rider_id, exc)
            self.path = [target]
            self.special_case = False
        self.target = target

    def _advance(self, now: int) -> None:
        """Move along the planned path by up to ``speed`` units."""
        budget = self.speed
        while budget > 0 and self.path:
            nxt = self.path[0]
            if self._is_blocked(nxt):
                if self.wait_ticks < MAX_WAIT_TICKS:
                    self.wait_ticks += 1
                    return
                logger.warning("Rider %d: forcing progress to avoid deadlock",
                               self.rider_id)
            self.wait_ticks = 0
            dx = nxt[0] - self.x
            dy = nxt[1] - self.y
            distance = abs(dx) + abs(dy)
            if distance <= budget:
                self.x, self.y = nxt
                self.path.pop(0)
                budget -= distance
            else:
                if dx:
                    self.x += budget if dx > 0 else -budget
                else:
                    self.y += budget if dy > 0 else -budget
                budget = 0

    def _is_blocked(self, nxt: Point) -> bool:
        """Conflict avoidance for the next lattice node.

        A rider yields when another rider occupies the next node and either
        the two riders head towards each other (the higher ID yields) or the
        occupant is stationary.
        """
        for other in get_value("riders", []) or []:
            if other is self or other.position != nxt:
                continue
            if other.path and other.path[0] == self.position \
                    and other.rider_id < self.rider_id:
                return True
            if not other.path:
                return True
        return False

    def _handle_arrivals(self, now: int) -> None:
        """Process arrivals at the current target, possibly several in a row."""
        while self.state != IDLE and self.target is not None \
                and self.position == self.target:
            if self.state == PICKING_UP:
                self._arrive_at_merchant(now)
            elif self.state == DELIVERING:
                self._deliver(now)
            else:
                break

    def _arrive_at_merchant(self, now: int) -> None:
        """Collect the food and start the delivery leg."""
        order = self.orders[0]
        self._record("arrived_at_merchant", order.id)
        self.state = DELIVERING
        order.mark_picked_up(now)
        self._plan_to(order.customer_pos, order)

    def _deliver(self, now: int) -> None:
        """Complete the current order and start the next one if queued."""
        order = self.orders[0]
        self._record("delivered_to_customer", order.id)
        order.complete(now)
        self.orders.pop(0)
        self.state = IDLE
        self.target = None
        self.path = []
        self.special_case = False
        self.wait_ticks = 0
        if self.orders:
            self._accept_order(now)

    def __repr__(self) -> str:
        return (f"Rider(id={self.rider_id}, pos=({self.x},{self.y}), "
                f"state={self.state_name}, orders={len(self.orders)})")
