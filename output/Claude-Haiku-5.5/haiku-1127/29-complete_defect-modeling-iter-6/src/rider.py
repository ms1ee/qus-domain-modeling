"""Rider model: state machine, movement and order execution.

State machine:
    IDLE (0) -> PICKING_UP (1) when the first assigned order is accepted.
    PICKING_UP (1) -> DELIVERING (2) on arrival at the restaurant.
    DELIVERING (2) -> IDLE (0) on delivery to the customer.

Log entries are appended to ``Rider.log`` as dictionaries with the keys
``event``, ``order_id``, ``tick``, ``rider_id``, ``x``, ``y`` and ``state``.
Events: "spawn", "accepted_order", "arrived_at_merchant",
"delivered_to_customer".
"""

import logging
from typing import Any, Dict, List, Optional, Tuple

import globalvar
from grid import CELL_SIZE
from path_planner import PathPlanner

logger = logging.getLogger(__name__)

IDLE = 0
PICKING_UP = 1
DELIVERING = 2

STATE_NAMES = {
    IDLE: "idle",
    PICKING_UP: "picking up",
    DELIVERING: "delivering",
}

DEFAULT_RIDER_SPEED = 50


class Rider:
    """A delivery rider that moves on the grid and executes orders.

    Attributes:
        rider_id: Unique integer identifier.
        x, y: Current integer coordinates.
        speed: Movement speed in units per tick.
        state: 0 idle, 1 picking up, 2 delivering.
        orders: Assigned orders; ``orders[0]`` is the one being served.
        special_case: True while the rider is off-street (inside a cell).
        log: Chronological list of status-change entries.
    """

    def __init__(self, rider_id: int, x: int = 0, y: int = 0,
                 speed: int = DEFAULT_RIDER_SPEED,
                 planner: Optional[PathPlanner] = None) -> None:
        """Create a rider and record its spawn event.

        Args:
            rider_id: Unique identifier.
            x: Initial x coordinate.
            y: Initial y coordinate.
            speed: Movement speed in units per tick.
            planner: Shared path planner; a new one is created if omitted.
        """
        self.rider_id = int(rider_id)
        self.x = int(x)
        self.y = int(y)
        self.speed = int(speed)
        self.state = IDLE
        self.orders: List[Any] = []
        self.special_case = False
        self.planner = planner if planner is not None else PathPlanner()
        self.log: List[Dict[str, Any]] = []
        self._waypoints: List[Tuple[int, int]] = []
        self._record("spawn", None)

    @property
    def position(self) -> Tuple[int, int]:
        """Current position as an (x, y) tuple."""
        return (self.x, self.y)

    def is_idle(self) -> bool:
        """Return True when the rider is available for new work."""
        return self.state == IDLE

    def _now(self) -> int:
        """Return the current simulated tick from the global store."""
        tick = globalvar.get_value("current_tick", 0)
        return tick if isinstance(tick, int) else 0

    def _record(self, event: str, order_id: Optional[int]) -> None:
        """Append a status-change entry to the rider log."""
        entry = {
            "event": event,
            "order_id": order_id,
            "tick": self._now(),
            "rider_id": self.rider_id,
            "x": self.x,
            "y": self.y,
            "state": self.state,
        }
        self.log.append(entry)
        logger.debug("Rider %d: %s (order %s)", self.rider_id, event,
                     order_id)

    def _distance_to(self, point: Tuple[int, int]) -> int:
        """Return the Manhattan distance from the rider to a point."""
        return abs(point[0] - self.x) + abs(point[1] - self.y)

    def _reset_to_idle(self) -> None:
        """Set the rider to idle and drop any planned waypoints."""
        self.state = IDLE
        self._waypoints = []
        self.special_case = False

    def _start_pickup(self) -> None:
        """Accept the first order and plan the route to the restaurant.

        With several assigned orders, the unpicked orders are sorted by
        distance from the rider so that the nearest restaurant is visited
        first (multi-destination ordering).
        """
        if len(self.orders) > 1:
            self.orders.sort(key=lambda o: self._distance_to(o.restaurant_pos))
        order = self.orders[0]
        self.state = PICKING_UP
        self._record("accepted_order", order.id)
        route = self.planner.plan(self.position, order.restaurant_pos,
                                  self.speed)
        self._waypoints = list(route.waypoints)
        order.record_route(self.position, route.waypoints)

    def _advance(self) -> None:
        """Move up to ``speed`` units along the planned waypoints."""
        x, y, remaining, moved = self.planner.step(
            self.x, self.y, self._waypoints, self.speed)
        self.x, self.y = x, y
        self._waypoints = remaining
        if self.orders:
            self.orders[0].distance += moved
        self.special_case = (x % CELL_SIZE != 0 and y % CELL_SIZE != 0)

    def _handle_arrival(self) -> Optional[Any]:
        """Process arrival at the current target.

        Returns:
            The completed Order if a delivery finished, otherwise None.
        """
        order = self.orders[0]
        if self.state == PICKING_UP:
            order.mark_picked_up()
            self.state = DELIVERING
            self._record("arrived_at_merchant", order.id)
            route = self.planner.plan(self.position, order.customer_pos,
                                      self.speed)
            self._waypoints = list(route.waypoints)
            order.record_route(self.position, route.waypoints)
            return None
        if self.state == DELIVERING:
            order.complete(self._now())
            self.orders.pop(0)
            self._record("delivered_to_customer", order.id)
            self._reset_to_idle()
            logger.info("Rider %d delivered order %d", self.rider_id,
                        order.id)
            return order
        return None

    def move(self) -> List[Any]:
        """Advance the rider by one tick.

        Performs state transitions, movement and arrival handling.

        Returns:
            List of orders completed during this tick.
        """
        completed: List[Any] = []
        if not self.orders:
            if self.state != IDLE:
                logger.warning(
                    "Rider %d in state %d without orders; resetting to idle",
                    self.rider_id, self.state)
                self._reset_to_idle()
            return completed
        if self.state == IDLE:
            self._start_pickup()
        if self._waypoints:
            self._advance()
        while self.orders and self.state != IDLE and not self._waypoints:
            finished = self._handle_arrival()
            if finished is not None:
                completed.append(finished)
        return completed
