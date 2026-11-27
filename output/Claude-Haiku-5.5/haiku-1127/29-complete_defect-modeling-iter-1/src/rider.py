"""Rider model: state machine, grid movement and event logging."""

import logging
from typing import Any, Dict, List, Set

import globalvar
from path_planner import Point, PathPlanner

LOGGER = logging.getLogger(__name__)

STATE_IDLE = 0
STATE_PICKING_UP = 1
STATE_DELIVERING = 2
STATE_NAMES = {
    STATE_IDLE: "idle",
    STATE_PICKING_UP: "picking up",
    STATE_DELIVERING: "delivering",
}
SPAWN_POINT: Point = (50, 50)


def _clamp_step(delta: int, speed: int) -> int:
    """Limit a signed distance to at most ``speed`` units in magnitude."""
    if delta > 0:
        return min(delta, speed)
    return max(delta, -speed)


class Rider:
    """A delivery rider that moves along streets and serves orders in FIFO order.

    The state machine is:
        idle (0) -> picking up (1) when an order is accepted;
        picking up (1) -> delivering (2) on arrival at the restaurant;
        delivering (2) -> idle (0) on delivery to the customer.

    Every transition and the arrival/acceptance moments are recorded in
    ``self.log`` as dictionaries containing at least the keys ``"event"`` and
    ``"order_id"``.
    """

    def __init__(self, rider_id: int) -> None:
        """Create an idle rider at the spawn point and log the spawn event.

        Args:
            rider_id: Unique rider identifier.
        """
        self.rider_id: int = int(rider_id)
        self.x, self.y = SPAWN_POINT
        self.speed: int = max(1, int(globalvar.get_value("rider_speed", 50)))
        self.state: int = STATE_IDLE
        self.orders: List[Any] = []
        self.special_case: bool = False
        self.path: List[Point] = []
        self.planner = PathPlanner()
        self.distance_traveled: int = 0
        self.log: List[Dict[str, Any]] = []
        self._record("spawn", None)

    @property
    def position(self) -> Point:
        """Current ``(x, y)`` position."""
        return (self.x, self.y)

    def _now(self) -> int:
        """Return the current simulated time in ticks."""
        return int(globalvar.get_value("simulated_time", 0))

    def _record(self, event: str, order_id: Any) -> None:
        """Append a status-change entry to the rider log.

        Args:
            event: Event name such as ``"accepted_order"``.
            order_id: Related order ID, or None.
        """
        entry = {
            "time": self._now(),
            "event": event,
            "order_id": order_id,
            "rider_id": self.rider_id,
            "state": self.state,
            "x": self.x,
            "y": self.y,
        }
        self.log.append(entry)
        LOGGER.info(
            "rider=%s t=%s event=%s order=%s pos=(%s,%s)",
            self.rider_id,
            entry["time"],
            event,
            order_id,
            self.x,
            self.y,
        )

    def _other_positions(self) -> Set[Point]:
        """Return positions of all other riders, used for conflict avoidance."""
        return {
            rider.position
            for rider in globalvar.get_value("riders", [])
            if rider is not self
        }

    def _target_for_state(self) -> Point:
        """Return the grid point the rider should currently be heading to."""
        order = self.orders[0]
        if self.state == STATE_PICKING_UP:
            return order.res_pos
        return order.cus_pos

    def move(self) -> None:
        """Advance the rider by one simulation tick.

        Handles order acceptance (idle -> picking up), movement along the
        planned route, arrival at the restaurant (picking up -> delivering)
        and delivery to the customer (delivering -> idle).
        """
        if self.state == STATE_IDLE:
            if not self.orders:
                return
            self._accept_order(self.orders[0])
        elif not self.path and self.orders:
            # Recovery path: an active order without a planned leg.
            self._begin_leg(self._target_for_state())
        if self.path:
            self._step()

    def _accept_order(self, order: Any) -> None:
        """Transition to picking up and plan the leg to the restaurant.

        Args:
            order: The order being accepted (first in the rider's queue).
        """
        self.state = STATE_PICKING_UP
        order.status = "picking_up"
        if not order.route:
            order.route.append(self.position)
        self._record("accepted_order", order.id)
        self._begin_leg(order.res_pos)

    def _begin_leg(self, goal: Point) -> None:
        """Plan the route from the current position to ``goal``.

        If the rider is already at the goal, the arrival is processed
        immediately.

        Args:
            goal: Destination grid point.
        """
        here = self.position
        self.special_case = PathPlanner.is_special_case(here, goal)
        self.path = self.planner.plan(here, goal, self._other_positions())
        if not self.path:
            self._on_arrival()

    def _step(self) -> None:
        """Move one tick toward the next waypoint along a street."""
        tx, ty = self.path[0]
        moved = 0
        if self.x != tx:
            delta = _clamp_step(tx - self.x, self.speed)
            self.x += delta
            moved = abs(delta)
        elif self.y != ty:
            delta = _clamp_step(ty - self.y, self.speed)
            self.y += delta
            moved = abs(delta)

        if moved:
            self.distance_traveled += moved
            if self.orders:
                order = self.orders[0]
                order.distance += moved
                order.route.append(self.position)

        if self.position == (tx, ty):
            self.path.pop(0)
            if not self.path:
                self._on_arrival()

    def _on_arrival(self) -> None:
        """Handle reaching the end of the current leg."""
        if not self.orders:
            self.state = STATE_IDLE
            self.special_case = False
            return

        order = self.orders[0]
        if self.state == STATE_PICKING_UP:
            self.state = STATE_DELIVERING
            order.status = "delivering"
            self._record("arrived_at_merchant", order.id)
            self._begin_leg(order.cus_pos)
        elif self.state == STATE_DELIVERING:
            order.mark_completed(self._now())
            self.orders.pop(0)
            self.state = STATE_IDLE
            self.special_case = False
            self._record("delivered_to_customer", order.id)
            if self.orders:
                self._accept_order(self.orders[0])

    def to_dict(self) -> Dict[str, Any]:
        """Return a JSON-serializable snapshot of this rider."""
        return {
            "rider_id": self.rider_id,
            "x": self.x,
            "y": self.y,
            "speed": self.speed,
            "state": self.state,
            "special_case": self.special_case,
            "orders": [order.id for order in self.orders],
            "distance_traveled": self.distance_traveled,
            "log": list(self.log),
        }
