"""Rider model: state machine, street movement, and event logging.

State machine::

    IDLE (0)  --accepted order-->  PICKING_UP (1)
    PICKING_UP (1)  --reached restaurant-->  DELIVERING (2)
    DELIVERING (2)  --delivered to customer-->  IDLE (0)
"""

import logging
import random
from typing import Any, Dict, List, Optional

from globalvar import get_value
from order import record_completion
from order_model import STATUS_DELIVERING, STATUS_PICKING_UP, Order
from path_planner import PathPlanner, Point

logger = logging.getLogger(__name__)

IDLE = 0
PICKING_UP = 1
DELIVERING = 2

STATE_NAMES = {
    IDLE: "idle",
    PICKING_UP: "picking up",
    DELIVERING: "delivering",
}

SPEED_CHOICES = (60, 80, 100)
MAX_WAIT_TICKS = 3


class Rider:
    """A delivery rider that moves along streets and serves orders in sequence.

    Attributes:
        rider_id: Unique identifier.
        x: Current horizontal coordinate.
        y: Current vertical coordinate.
        speed: Movement speed in units per tick.
        state: Current state (IDLE, PICKING_UP, or DELIVERING).
        orders: Assigned orders; the first element is the active order.
        special_case: True when the current target is directly above or below
            the rider (same x or y), i.e. a straight-line movement.
        path: Remaining street points to visit, in order.
        target: Current destination point, or None when idle.
        wait_ticks: Consecutive ticks spent waiting for a blocked point.
        distance_travelled: Total units moved.
        log: Event history entries with keys ``tick``, ``event``, ``order_id``,
            ``x``, ``y``, ``state``, and ``rider_id``.
    """

    def __init__(self, rider_id: int, rng: Optional[random.Random] = None) -> None:
        """Spawn a rider on a random street with an idle state.

        Args:
            rider_id: Unique identifier assigned by the system.
            rng: Optional random generator for placement and speed.
        """
        self.rider_id: int = rider_id
        self._rng: random.Random = rng if rng is not None else random.Random()
        self.planner = PathPlanner(self._rng)
        self.x, self.y = self.planner.random_road_point()
        self.speed: int = self._rng.choice(SPEED_CHOICES)
        self.state: int = IDLE
        self.orders: List[Order] = []
        self.special_case: bool = False
        self.path: List[Point] = []
        self.target: Optional[Point] = None
        self.wait_ticks: int = 0
        self.distance_travelled: int = 0
        self.log: List[Dict[str, Any]] = []
        self._record("spawn", None)

    def position(self) -> Point:
        """Return the current position as ``(x, y)``."""
        return (self.x, self.y)

    @property
    def state_name(self) -> str:
        """Human-readable name of the current state."""
        return STATE_NAMES.get(self.state, "unknown")

    def move(self) -> None:
        """Advance the rider by one tick.

        An idle rider with orders accepts the first one and starts moving to
        the restaurant. The rider moves up to ``speed`` street units along its
        path, and state transitions happen when it reaches a target.
        """
        if self.state == IDLE:
            if not self.orders:
                return
            self._start_pickup()

        self._advance()

        for _ in range(2):
            if self.state == IDLE or self.path or self.target is None:
                break
            self._reach_target()

    def _start_pickup(self) -> None:
        """Accept the next order and head toward its restaurant."""
        order = self.orders[0]
        order.status = STATUS_PICKING_UP
        self.state = PICKING_UP
        self._set_target(order.res_pos)
        self._record("accepted_order", order.id)

    def _set_target(self, target: Point) -> None:
        """Set a new destination and compute the street path to reach it.

        Args:
            target: Destination point on a street.
        """
        self.target = target
        path = self.planner.find_path(self.position(), target)
        if path is None:
            logger.warning("Rider %s found no path to %s", self.rider_id, target)
            path = []
        self.path = path
        self.special_case = (
            (self.x == target[0] or self.y == target[1])
            and self.position() != target
        )

    def _advance(self) -> None:
        """Move along the path by up to ``speed`` units, respecting blocking."""
        steps = self.speed
        while steps > 0 and self.path:
            if self._is_blocked():
                self.wait_ticks += 1
                break
            self.wait_ticks = 0
            self.x, self.y = self.path.pop(0)
            self.distance_travelled += 1
            steps -= 1

    def _is_blocked(self) -> bool:
        """Return True when the next point is held by another rider.

        A rider waits at most ``MAX_WAIT_TICKS`` ticks, then proceeds. This
        prevents deadlocks when two riders block each other.
        """
        if not self.path:
            return False
        if self.wait_ticks >= MAX_WAIT_TICKS:
            return False
        nxt = self.path[0]
        for other in get_value("riders", []):
            if other is not self and other.position() == nxt:
                return True
        return False

    def _reach_target(self) -> None:
        """Handle arrival at the current target and perform the state transition."""
        if not self.orders:
            self._become_idle()
            return
        order = self.orders[0]
        if self.state == PICKING_UP:
            self.state = DELIVERING
            order.status = STATUS_DELIVERING
            self._record("arrived_at_merchant", order.id)
            self._set_target(order.cus_pos)
        elif self.state == DELIVERING:
            tick = int(get_value("tick", 0))
            order.complete(tick)
            self._record("delivered_to_customer", order.id)
            self.orders.pop(0)
            record_completion(order)
            self._become_idle()

    def _become_idle(self) -> None:
        """Reset the rider to the idle state with no active destination."""
        self.state = IDLE
        self.target = None
        self.path = []
        self.special_case = False
        self.wait_ticks = 0

    def _record(self, event: str, order_id: Optional[int]) -> None:
        """Append an entry to the rider's event log.

        Args:
            event: Event name, e.g. ``"accepted_order"``.
            order_id: Related order ID, or None.
        """
        self.log.append({
            "tick": int(get_value("tick", 0)),
            "event": event,
            "order_id": order_id,
            "rider_id": self.rider_id,
            "x": self.x,
            "y": self.y,
            "state": self.state,
        })

    def to_dict(self) -> Dict[str, Any]:
        """Return a JSON-serialisable representation of the rider."""
        return {
            "rider_id": self.rider_id,
            "x": self.x,
            "y": self.y,
            "speed": self.speed,
            "state": self.state,
            "orders": [o.id for o in self.orders],
            "special_case": self.special_case,
            "distance_travelled": self.distance_travelled,
            "log": list(self.log),
        }
