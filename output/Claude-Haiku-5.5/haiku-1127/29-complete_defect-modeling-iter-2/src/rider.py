"""Rider entity: state machine, grid movement and status logging.

Rider state machine:
    IDLE (0) -> PICKING_UP (1) when the first queued order is accepted.
    PICKING_UP (1) -> DELIVERING (2) on arrival at the restaurant.
    DELIVERING (2) -> IDLE (0) on delivery, or PICKING_UP (1) for the next
    queued order if one remains.

Riders may share street nodes. Movement never blocks, so no deadlock can form.
"""

import logging
from typing import Any, Dict, List, Optional, Tuple

from globalvar import get_value
from location import cell_center
from path_planner import default_planner
from settings import CONFIG

logger = logging.getLogger("dispatch")

IDLE = 0
PICKING_UP = 1
DELIVERING = 2
STATE_NAMES = {IDLE: "idle", PICKING_UP: "picking up", DELIVERING: "delivering"}

Point = Tuple[int, int]


def _now() -> int:
    """Return the current simulated time, or 0 if it is unset."""
    value = get_value("simulated_time")
    return value if isinstance(value, int) else 0


class Rider:
    """A delivery rider that moves along the street grid.

    Attributes:
        rider_id: Unique identifier.
        x, y: Current position in map units.
        speed: Movement speed in units per tick.
        state: IDLE, PICKING_UP, or DELIVERING.
        orders: Assigned orders. ``orders[0]`` is the active order.
        special_case: True while the rider is aligned with its current target.
        route: Remaining waypoints ``(x, y)`` of the current leg.
        leg_target: Point the current leg is heading to, or None.
        log: Status change records, each a dict with keys ``time``, ``event``,
            ``order_id``, ``location``, ``state`` and ``rider_id``.
        distance_travelled: Total distance moved, in map units.
    """

    def __init__(self, rider_id: int) -> None:
        """Create a rider at the hub and log its spawn event.

        Args:
            rider_id: Unique identifier assigned by the system.
        """
        self.rider_id = rider_id
        hub = cell_center(0)
        self.x = hub
        self.y = hub
        self.speed = CONFIG["rider_speed"]
        self.state = IDLE
        self.orders: List[Any] = []
        self.special_case = False
        self.route: List[Point] = []
        self.leg_target: Optional[Point] = None
        self.log: List[Dict[str, Any]] = []
        self.distance_travelled = 0
        self._record("spawn", None)

    @property
    def position(self) -> Point:
        """Current ``(x, y)`` position."""
        return (self.x, self.y)

    @property
    def status_name(self) -> str:
        """Human-readable name of the current state."""
        return STATE_NAMES.get(self.state, "unknown")

    @property
    def current_order(self) -> Optional[Any]:
        """The order being served, or None if the rider has no orders."""
        return self.orders[0] if self.orders else None

    def move(self) -> None:
        """Advance this rider by one tick.

        Handles state transitions and their log entries:
        accepting an order, arriving at the restaurant, and delivering.
        """
        if not self.orders:
            if self.state != IDLE:
                self._set_state(IDLE)
            self.route = []
            self.leg_target = None
            self.special_case = False
            return

        if self.state == IDLE:
            self._begin_order(self.orders[0])

        if self.route:
            self._advance()
            if self.route:
                return

        if self.state == PICKING_UP:
            self._arrive_at_merchant()

        if self.state == DELIVERING and not self.route:
            self._deliver()

    def recover(self) -> None:
        """Re-plan the current leg after an inconsistency or exception."""
        self.route = []
        if not self.orders:
            self._set_state(IDLE)
            self.leg_target = None
            self.special_case = False
            return
        order = self.orders[0]
        if self.state == DELIVERING:
            self._plan_leg(order.cus_pos.center)
        else:
            self._set_state(PICKING_UP)
            self._plan_leg(order.res_pos.center)

    def to_dict(self) -> Dict[str, Any]:
        """Return a JSON-serialisable snapshot of this rider."""
        return {
            "rider_id": self.rider_id,
            "x": self.x,
            "y": self.y,
            "speed": self.speed,
            "state": self.state,
            "status": self.status_name,
            "orders": [order.id for order in self.orders],
            "special_case": self.special_case,
            "distance_travelled": self.distance_travelled,
            "log": list(self.log),
        }

    def _record(self, event: str, order_id: Optional[int]) -> None:
        """Append a status change record to the rider's log."""
        entry = {
            "time": _now(),
            "event": event,
            "order_id": order_id,
            "location": (self.x, self.y),
            "state": self.state,
            "rider_id": self.rider_id,
        }
        self.log.append(entry)
        logger.debug("Rider %s %s order=%s", self.rider_id, event, order_id)

    def _set_state(self, state: int) -> None:
        """Set the state value."""
        self.state = state

    def _begin_order(self, order: Any) -> None:
        """Accept an order: enter PICKING_UP and plan the route to the restaurant."""
        self._set_state(PICKING_UP)
        order.mark_accepted()
        self._record("accepted_order", order.id)
        self._plan_leg(order.res_pos.center)

    def _arrive_at_merchant(self) -> None:
        """Pick up the order and plan the route to the customer."""
        order = self.orders[0]
        order.mark_picked_up(_now())
        self._set_state(DELIVERING)
        self._record("arrived_at_merchant", order.id)
        self._plan_leg(order.cus_pos.center)

    def _deliver(self) -> None:
        """Complete the active order and start the next one, if any."""
        order = self.orders[0]
        order.complete(_now())
        self._record("delivered_to_customer", order.id)
        self.orders.pop(0)
        self.leg_target = None
        if self.orders:
            self._begin_order(self.orders[0])
        else:
            self._set_state(IDLE)
            self.special_case = False

    def _plan_leg(self, target: Point) -> None:
        """Plan the street route from the current position to ``target``."""
        self.leg_target = target
        route = default_planner().plan((self.x, self.y), target, self.speed)
        points = route.coordinates()
        if points and points[0] == (self.x, self.y):
            points = points[1:]
        self.route = points
        self.special_case = self.x == target[0] or self.y == target[1]

    def _advance(self) -> None:
        """Spend this tick's movement budget along the planned waypoints.

        Movement is axis-aligned along streets. A waypoint is removed once
        it is reached, and the rider never overshoots it.
        """
        budget = self.speed
        while budget > 0 and self.route:
            tx, ty = self.route[0]
            if self.x != tx:
                step = min(budget, abs(tx - self.x))
                self.x += step if tx > self.x else -step
            elif self.y != ty:
                step = min(budget, abs(ty - self.y))
                self.y += step if ty > self.y else -step
            else:
                self.route.pop(0)
                continue
            budget -= step
            self.distance_travelled += step
            if self.x == tx and self.y == ty:
                self.route.pop(0)
