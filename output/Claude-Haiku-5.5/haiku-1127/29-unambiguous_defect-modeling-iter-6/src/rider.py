"""Rider model: movement, state transitions and status logging.

Rider states:
    0 (IDLE): no active order.
    1 (PICKING_UP): driving to the restaurant of ``orders[0]``.
    2 (DELIVERING): driving to the customer of ``orders[0]``.

An order is assigned by appending it to ``rider.orders``. Riders serve their
orders in FIFO order. ``move()`` advances the rider by one tick and performs
all state transitions and log entries.
"""

import logging
import random
from collections import deque
from typing import Any, Deque, Dict, List, Optional, Tuple

import globalvar
from path_planner import STEP, PathPlanner

logger = logging.getLogger(__name__)

IDLE = 0
PICKING_UP = 1
DELIVERING = 2
STATE_NAMES = {IDLE: "idle", PICKING_UP: "picking up", DELIVERING: "delivering"}

SPEED_CHOICES = (50, 100)
MAX_WAIT_TICKS = 3
MAX_LOG_ENTRIES = 10000

_planner = PathPlanner()


def _current_tick() -> int:
    """Return the current simulated tick from the global store."""
    return int(globalvar.get_value("current_tick", 0) or 0)


class Rider:
    """A delivery rider placed on a street.

    Attributes:
        rider_id: Unique rider identifier.
        x, y: Current position (always on a street, except at a location).
        speed: Movement budget in units per tick (50 or 100).
        state: 0 idle, 1 picking up, 2 delivering.
        orders: Assigned orders, served in order.
        special_case: True when the rider is at a location or directly
            above/below its target.
        log: Status change records. Each entry is a dict with keys
            ``tick``, ``event``, ``order_id``, ``x``, ``y`` and ``state``.
    """

    def __init__(self, rider_id: int) -> None:
        """Create a rider on a random street with an idle state.

        Args:
            rider_id: Unique identifier assigned by the system.
        """
        self.rider_id = rider_id
        self.x, self.y = _planner.random_road_node()
        self.speed = random.choice(SPEED_CHOICES)
        self.state = IDLE
        self.orders: List[Any] = []
        self.special_case = False
        self.path: Deque[Tuple[int, int]] = deque()
        self.target: Optional[Tuple[int, int]] = None
        self.wait_ticks = 0
        self.distance_travelled = 0
        self.log: List[Dict[str, Any]] = []
        self._record("spawn", None)

    @property
    def position(self) -> Tuple[int, int]:
        """Current ``(x, y)`` position."""
        return (self.x, self.y)

    @property
    def state_name(self) -> str:
        """Human-readable state name."""
        return STATE_NAMES.get(self.state, "unknown")

    @property
    def load(self) -> int:
        """Number of orders currently assigned."""
        return len(self.orders)

    def move(self) -> None:
        """Advance the rider by one tick.

        Order of operations:
            1. An idle rider with orders starts the pickup (IDLE -> PICKING_UP).
            2. The rider moves up to ``speed // STEP`` street steps, yielding
               to riders on the next node for a short time to avoid deadlock.
            3. On arrival at the restaurant, the state becomes DELIVERING.
               On arrival at the customer, the order completes and the state
               becomes IDLE.
        """
        if self.state == IDLE:
            if not self.orders:
                return
            if not self._begin_pickup():
                return

        if self.path:
            self._advance()

        if not self.path and self.target is not None:
            self._handle_arrival()

        self._update_special_case()

    def to_dict(self) -> Dict[str, Any]:
        """Return a JSON-serialisable representation of the rider."""
        return {
            "rider_id": self.rider_id,
            "x": self.x,
            "y": self.y,
            "speed": self.speed,
            "state": self.state,
            "state_name": self.state_name,
            "special_case": self.special_case,
            "orders": [order.id for order in self.orders],
            "distance_travelled": self.distance_travelled,
        }

    def _record(self, event: str, order_id: Optional[int]) -> None:
        """Append a status change entry to the rider log."""
        self.log.append(
            {
                "tick": _current_tick(),
                "event": event,
                "order_id": order_id,
                "x": self.x,
                "y": self.y,
                "state": self.state,
            }
        )
        if len(self.log) > MAX_LOG_ENTRIES:
            del self.log[: len(self.log) - MAX_LOG_ENTRIES]

    def _begin_pickup(self) -> bool:
        """Plan a route to the restaurant of the first order.

        Returns:
            True if the pickup started, False if no route was found.
        """
        order = self.orders[0]
        path = _planner.find_path(self.position, order.restaurant_pos)
        if path is None:
            self._fail(order, "no route to restaurant")
            return False
        self.path = deque(path)
        self.target = order.restaurant_pos
        self.state = PICKING_UP
        order.set_status("picking_up")
        order.distance += _planner.path_length_units(path)
        self._record("accepted_order", order.id)
        return True

    def _advance(self) -> None:
        """Move along the planned path for this tick."""
        steps = max(1, self.speed // STEP)
        for _ in range(steps):
            if not self.path:
                break
            nxt = self.path[0]
            if self._blocked(nxt) and self.wait_ticks < MAX_WAIT_TICKS:
                self.wait_ticks += 1
                break
            self.wait_ticks = 0
            self.path.popleft()
            self.x, self.y = nxt
            self.distance_travelled += STEP

    def _handle_arrival(self) -> None:
        """Apply the state transition for a completed leg of the route."""
        if not self.orders:
            self.target = None
            self.state = IDLE
            return
        order = self.orders[0]

        if self.state == PICKING_UP and self.position == order.restaurant_pos:
            self._record("arrived_at_merchant", order.id)
            path = _planner.find_path(self.position, order.customer_pos)
            if path is None:
                self._fail(order, "no route to customer")
                return
            self.path = deque(path)
            self.target = order.customer_pos
            self.state = DELIVERING
            order.set_status("delivering")
            order.distance += _planner.path_length_units(path)

        elif self.state == DELIVERING and self.position == order.customer_pos:
            self._record("delivered_to_customer", order.id)
            order.complete(_current_tick())
            self.orders.pop(0)
            self.target = None
            self.state = IDLE
            self.special_case = False

    def _fail(self, order: Any, reason: str) -> None:
        """Abort an order that cannot be routed and free the rider."""
        logger.error("Rider #%s cannot serve order #%s: %s",
                     self.rider_id, order.id, reason)
        self._record("route_error", order.id)
        if self.orders and self.orders[0] is order:
            self.orders.pop(0)
        order.set_status("failed")
        self.path.clear()
        self.target = None
        self.state = IDLE

    def _blocked(self, node: Tuple[int, int]) -> bool:
        """Return True if another rider occupies ``node``."""
        for other in globalvar.get_value("riders", []) or []:
            if other is not self and other.position == node:
                return True
        return False

    def _update_special_case(self) -> None:
        """Refresh the special_case flag.

        The flag is True when the rider stands on a location center, or when
        it is directly above or below its current target.
        """
        special = _planner.grid.is_location(self.x, self.y)
        if self.target is not None and self.x == self.target[0]:
            special = True
        self.special_case = special
