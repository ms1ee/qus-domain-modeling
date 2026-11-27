"""Rider model: state machine, movement and order execution.

Rider states:
    0 - idle (available for new orders)
    1 - picking up (en route to the restaurant)
    2 - delivering (en route to the customer)

Transitions:
    idle -> picking up   when an order is appended to ``orders``
    picking up -> delivering  on arrival at the restaurant
    delivering -> idle   on delivery (or -> picking up for the next order)
"""

import logging
from typing import Any, Dict, List, Optional, Tuple

import config
import globalvar
from grid import Point
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

# Depot where every newly recruited rider starts (a street intersection).
DEPOT: Point = (0, 0)


class Rider:
    """A delivery rider moving on the street grid.

    Attributes:
        rider_id: Unique identifier.
        x, y: Current coordinates in units (0-800).
        speed: Movement in units per tick.
        state: 0 idle, 1 picking up, 2 delivering.
        orders: Assigned orders; ``orders[0]`` is the one being executed.
        special_case: True while the rider is waiting for a blocked cell.
        route: Remaining waypoints for the current target.
        log: Chronological list of event dictionaries.
    """

    def __init__(
        self,
        rider_id: int,
        x: int = DEPOT[0],
        y: int = DEPOT[1],
        speed: Optional[int] = None,
    ) -> None:
        """Create a rider and record its spawn event.

        Args:
            rider_id: Unique rider identifier.
            x: Initial x coordinate (defaults to the depot).
            y: Initial y coordinate (defaults to the depot).
            speed: Units per tick; defaults to the configured rider speed.

        Raises:
            ValueError: If the speed is not positive.
        """
        if speed is None:
            speed = int(config.CONFIG["rider_speed"])
        if speed <= 0:
            raise ValueError("rider speed must be positive")
        self.rider_id: int = rider_id
        self.x: int = x
        self.y: int = y
        self.speed: int = speed
        self.state: int = STATE_IDLE
        self.orders: List[Any] = []
        self.special_case: bool = False
        self.route: List[Point] = []
        self.wait_ticks: int = 0
        self.completed_count: int = 0
        self.log: List[Dict[str, Any]] = []
        self._planner = PathPlanner()
        self._record("spawn", None)
        logger.info(
            "Rider %d spawned at (%d, %d)", self.rider_id, self.x, self.y
        )

    @property
    def position(self) -> Point:
        """Current ``(x, y)`` position."""
        return (self.x, self.y)

    @property
    def state_name(self) -> str:
        """Human readable name of the current state."""
        return STATE_NAMES.get(self.state, "unknown")

    def move(self) -> Optional[Any]:
        """Advance the rider by one tick.

        Handles state transitions, movement along the planned route, arrival
        detection, and order completion.

        Returns:
            The completed Order if a delivery finished during this tick,
            otherwise None.
        """
        now = self._now()
        if self.state == STATE_IDLE and self.orders:
            self._start_pickup(now)
        if not self.orders:
            if self.state != STATE_IDLE:
                self._become_idle()
            return None

        order = self.orders[0]
        target = self._target_for_state(order)
        if self.position == target:
            return self._on_arrival(order, now)
        if not self.route:
            self.route = self._planner.plan(self.position, target)
        if not self._travel():
            return None
        if self.position == target:
            return self._on_arrival(order, now)
        return None

    def to_dict(self) -> Dict[str, Any]:
        """Return a JSON-serialisable snapshot of the rider."""
        return {
            "rider_id": self.rider_id,
            "x": self.x,
            "y": self.y,
            "speed": self.speed,
            "state": self.state,
            "orders": [order.id for order in self.orders],
            "special_case": self.special_case,
            "completed_count": self.completed_count,
            "log": list(self.log),
        }

    def _now(self) -> int:
        """Return the current simulated tick."""
        return int(globalvar.get_value("tick", 0))

    def _record(self, event: str, order_id: Optional[int]) -> None:
        """Append an event entry to the rider log."""
        self.log.append(
            {
                "event": event,
                "order_id": order_id,
                "time": self._now(),
                "rider_id": self.rider_id,
                "x": self.x,
                "y": self.y,
                "state": self.state,
            }
        )

    def _target_for_state(self, order: Any) -> Point:
        """Return the destination matching the current state."""
        if self.state == STATE_PICKING_UP:
            return order.restaurant_center
        return order.customer_center

    def _start_pickup(self, now: int) -> None:
        """Transition idle -> picking up for the first order."""
        self.state = STATE_PICKING_UP
        self.route = []
        self.wait_ticks = 0
        order = self.orders[0]
        self._record("accepted_order", order.id)
        logger.info(
            "Tick %d: rider %d accepted order %d",
            now,
            self.rider_id,
            order.id,
        )

    def _become_idle(self) -> None:
        """Return the rider to the idle state."""
        self.state = STATE_IDLE
        self.route = []
        self.special_case = False
        self.wait_ticks = 0

    def _on_arrival(self, order: Any, now: int) -> Optional[Any]:
        """Handle arrival at the current target.

        Returns:
            The order if it was delivered, otherwise None.
        """
        self.route = []
        if self.state == STATE_PICKING_UP:
            self.state = STATE_DELIVERING
            order.mark_picked_up(now)
            self._record("arrived_at_merchant", order.id)
            logger.info(
                "Tick %d: rider %d picked up order %d",
                now,
                self.rider_id,
                order.id,
            )
            return None
        if self.state == STATE_DELIVERING:
            order.complete(now)
            self._record("delivered_to_customer", order.id)
            logger.info(
                "Tick %d: rider %d delivered order %d",
                now,
                self.rider_id,
                order.id,
            )
            self.orders.pop(0)
            self.completed_count += 1
            if self.orders:
                self._start_pickup(now)
            else:
                self._become_idle()
            return order
        return None

    def _travel(self) -> bool:
        """Move up to ``speed`` units along the planned route.

        Movement is along the axis of the next waypoint. If the destination
        cell is occupied by another rider, the rider waits for a few ticks
        (special case) before proceeding anyway to break deadlocks.

        Returns:
            True if the rider moved (or the deadlock breaker fired),
            False if the rider is waiting.
        """
        x, y = self.x, self.y
        route = list(self.route)
        budget = self.speed
        while budget > 0 and route:
            wx, wy = route[0]
            if (x, y) == (wx, wy):
                route.pop(0)
                continue
            dx = wx - x
            dy = wy - y
            if dx != 0:
                step = min(budget, abs(dx))
                x += step if dx > 0 else -step
            else:
                step = min(budget, abs(dy))
                y += step if dy > 0 else -step
            budget -= step

        if (x, y) != self.position and self._occupied((x, y)):
            self.special_case = True
            self.wait_ticks += 1
            if self.wait_ticks <= int(config.CONFIG["max_wait_ticks"]):
                logger.debug(
                    "Rider %d waiting for occupied cell %s",
                    self.rider_id,
                    (x, y),
                )
                return False
            logger.warning(
                "Rider %d breaking possible deadlock at %s",
                self.rider_id,
                (x, y),
            )

        self.wait_ticks = 0
        self.special_case = False
        self.x, self.y = x, y
        self.route = route
        return True

    def _occupied(self, point: Point) -> bool:
        """Return True if another rider currently occupies ``point``."""
        riders = globalvar.get_value("riders", []) or []
        return any(
            other is not self and other.position == point for other in riders
        )


def describe_position(rider: Rider) -> Tuple[int, int]:
    """Return the rider position as a tuple (helper for display code)."""
    return rider.position
