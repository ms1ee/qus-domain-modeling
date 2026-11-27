"""Rider entity: state machine, street movement and event logging.

Rider states
------------
* 0 (IDLE): no active order.
* 1 (PICKING_UP): travelling to the restaurant of ``orders[0]``.
* 2 (DELIVERING): travelling to the customer of ``orders[0]``.

Orders are served first-in first-out.  An order is assigned by appending it
to ``rider.orders``; the state transition happens during ``move()``.
"""

import logging
import random
from typing import Any, Dict, List, Optional, Tuple

import globalvar
from globalvar import PARAMS, get_value, set_value
from path_planner import PathPlanner, is_street_point, random_road_point

logger = logging.getLogger(__name__)

IDLE = 0
PICKING_UP = 1
DELIVERING = 2
STATE_NAMES: Dict[int, str] = {
    IDLE: "idle",
    PICKING_UP: "picking up",
    DELIVERING: "delivering",
}

Point = Tuple[int, int]

_PLANNER = PathPlanner()


class Rider:
    """A delivery rider that moves along streets and serves orders.

    Attributes:
        rider_id: Unique identifier.
        x, y: Current position in map units.
        speed: Movement speed in units per tick.
        state: Current state (0 idle, 1 picking up, 2 delivering).
        orders: Assigned orders, served in order.
        special_case: True while the rider is off the street network
            (on an access stub next to a restaurant or customer).
        route: Remaining waypoints for the current leg.
        log: Event records with keys ``event``, ``order_id``, ``tick``,
            ``x``, ``y`` and ``state``.
    """

    def __init__(self, rider_id: int) -> None:
        """Create a rider on a random street point, idle, with no orders.

        A ``spawn`` event is logged.

        Args:
            rider_id: Unique identifier assigned by the system manager.
        """
        self.rider_id: int = int(rider_id)
        self.speed: int = random.randint(
            PARAMS["rider_speed_min"], PARAMS["rider_speed_max"]
        )
        self.x, self.y = random_road_point()
        self.state: int = IDLE
        self.orders: List[Any] = []
        self.special_case: bool = False
        self.route: List[Point] = []
        self.log: List[Dict[str, Any]] = []
        self._record("spawn", None)
        logger.info("Rider %d spawned at (%d, %d)", self.rider_id, self.x, self.y)

    def position(self) -> Point:
        """Return the current position as ``(x, y)``."""
        return (self.x, self.y)

    def state_name(self) -> str:
        """Return a human-readable name for the current state."""
        return STATE_NAMES.get(self.state, "unknown")

    def _record(self, event: str, order_id: Optional[int]) -> None:
        """Append a log entry describing a key moment for this rider."""
        entry = {
            "event": event,
            "order_id": order_id,
            "tick": int(get_value("tick", 0)),
            "x": self.x,
            "y": self.y,
            "state": self.state,
        }
        self.log.append(entry)
        overflow = len(self.log) - PARAMS["log_cap"]
        if overflow > 0:
            del self.log[:overflow]
        logger.debug("Rider %d event %s order=%s", self.rider_id, event, order_id)

    def move(self) -> None:
        """Advance the rider by one tick.

        Starts pickup for a newly assigned order when idle, moves up to
        ``speed`` units along the current route, and handles arrival at the
        restaurant or the customer.
        """
        if self.state == IDLE:
            if not self.orders:
                return
            self._begin_pickup()
        if self.state == IDLE:
            return
        self._advance(self.speed)
        self.special_case = not is_street_point(self.x, self.y)
        if not self.route:
            self._handle_arrival()

    def _begin_pickup(self) -> None:
        """Start serving ``orders[0]``: enter PICKING_UP and plan the route."""
        order = self.orders[0]
        self.state = PICKING_UP
        order.mark_picking_up()
        self._record("accepted_order", order.id)
        self.route = _PLANNER.plan(self.position(), order.res_pos)

    def _handle_arrival(self) -> None:
        """Process arrival at the current destination and update the state.

        Arrival at the restaurant moves the rider to DELIVERING with a route
        to the customer.  Arrival at the customer completes the order, credits
        the delivery fee, and either starts the next queued order or goes IDLE.
        """
        tick = int(get_value("tick", 0))
        while not self.route and self.orders and self.state != IDLE:
            order = self.orders[0]
            if self.state == PICKING_UP:
                self._record("arrived_at_merchant", order.id)
                self.state = DELIVERING
                order.mark_delivering()
                self.route = _PLANNER.plan(self.position(), order.cus_pos)
            else:
                self._record("delivered_to_customer", order.id)
                order.complete()
                self.orders.pop(0)
                funds = int(get_value("system_funds", 0))
                set_value("system_funds", funds + PARAMS["delivery_fee"])
                self.state = IDLE
                logger.info(
                    "Rider %d delivered order %d at tick %d",
                    self.rider_id, order.id, tick,
                )
                if self.orders:
                    self._begin_pickup()

    def _advance(self, budget: int) -> None:
        """Consume up to ``budget`` units of movement along the route.

        Segments are axis-aligned, so each step changes only one coordinate.

        Args:
            budget: Maximum distance to travel this tick.
        """
        while budget > 0 and self.route:
            tx, ty = self.route[0]
            dx, dy = tx - self.x, ty - self.y
            distance = abs(dx) + abs(dy)
            if distance == 0:
                self.route.pop(0)
                continue
            if distance <= budget:
                self.x, self.y = tx, ty
                budget -= distance
                self.route.pop(0)
            else:
                if dx != 0:
                    self.x += budget if dx > 0 else -budget
                else:
                    self.y += budget if dy > 0 else -budget
                budget = 0

    def to_dict(self) -> Dict[str, Any]:
        """Return a JSON-serialisable snapshot of the rider."""
        return {
            "rider_id": self.rider_id,
            "x": self.x,
            "y": self.y,
            "speed": self.speed,
            "state": self.state,
            "special_case": self.special_case,
            "order_ids": [order.id for order in self.orders],
            "log": list(self.log),
        }
