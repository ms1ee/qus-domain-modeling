"""Rider model: street-based movement, state transitions and event log.

Rider state enumeration:
    0 = idle, 1 = picking up (heading to a restaurant),
    2 = delivering (carrying food to a customer).

A rider serves its order list first-in first-out. The first active order
determines the current target: the restaurant while the order is "assigned",
the customer once it is "picked_up".
"""

import logging
from typing import Any, Dict, List, Optional

import globalvar
from order_model import ORDER_ASSIGNED, ORDER_COMPLETED, ORDER_PICKED_UP
from path_planner import Point, PathPlanner

logger = logging.getLogger(__name__)

DEFAULT_SPEED = 20
DEFAULT_START: Point = (400, 400)

STATE_IDLE = 0
STATE_PICKING_UP = 1
STATE_DELIVERING = 2
STATE_LABELS = {
    STATE_IDLE: "idle",
    STATE_PICKING_UP: "picking up",
    STATE_DELIVERING: "delivering",
}

EVENT_SPAWN = "spawn"
EVENT_ACCEPTED = "accepted_order"
EVENT_ARRIVED = "arrived_at_merchant"
EVENT_DELIVERED = "delivered_to_customer"

ACTIVE_STATUSES = (ORDER_ASSIGNED, ORDER_PICKED_UP)


def _sign(value: int) -> int:
    """Return -1, 0 or 1 according to the sign of ``value``."""
    return (value > 0) - (value < 0)


class Rider:
    """A delivery rider that moves along streets and serves orders.

    Attributes:
        rider_id: Unique identifier.
        x, y: Current coordinates.
        speed: Movement budget per tick (units/tick).
        state: 0 idle, 1 picking up, 2 delivering.
        orders: All orders ever assigned, including completed ones.
        special_case: True while moving straight toward a target that is
            directly above or below the rider.
        log: List of status-change dictionaries with keys including
            "event" and "order_id".
    """

    def __init__(
        self,
        rider_id: int,
        x: int = DEFAULT_START[0],
        y: int = DEFAULT_START[1],
    ) -> None:
        """Create a rider and record its spawn event.

        Args:
            rider_id: Unique rider identifier.
            x: Initial x coordinate (defaults to 400).
            y: Initial y coordinate (defaults to 400).
        """
        self.rider_id = rider_id
        self.x = int(x)
        self.y = int(y)
        self.speed = DEFAULT_SPEED
        self.state = STATE_IDLE
        self.orders: List[Any] = []
        self.special_case = False
        self.log: List[Dict[str, Any]] = []
        self._accepted_ids = set()
        self._record(EVENT_SPAWN, None)

    # ------------------------------------------------------------------
    # Queries
    # ------------------------------------------------------------------
    @property
    def position(self) -> Point:
        """Return the current ``(x, y)`` position."""
        return (self.x, self.y)

    def active_orders(self) -> List[Any]:
        """Return orders that are assigned or picked up but not completed."""
        return [o for o in self.orders if o.status in ACTIVE_STATUSES]

    def active_order_count(self) -> int:
        """Return the number of active (unfinished) orders."""
        return len(self.active_orders())

    def is_idle(self) -> bool:
        """Return True if the rider is available for new orders."""
        return self.state == STATE_IDLE

    def current_order(self) -> Optional[Any]:
        """Return the order the rider is currently serving, if any."""
        for order in self.orders:
            if order.status in ACTIVE_STATUSES:
                return order
        return None

    def route_targets(self) -> List[Point]:
        """Return the ordered list of points the rider must visit.

        Restaurants are included only for orders not yet picked up.
        """
        targets: List[Point] = []
        for order in self.active_orders():
            if order.status == ORDER_ASSIGNED:
                targets.append(order.res_pos)
            targets.append(order.cus_pos)
        return targets

    # ------------------------------------------------------------------
    # Commands
    # ------------------------------------------------------------------
    def on_order_assigned(self, order: Any) -> None:
        """Register a newly assigned order: log acceptance and update state.

        Args:
            order: The order that was appended to ``self.orders``.
        """
        self._sync_assignments()

    def move(self) -> None:
        """Advance the rider by one tick.

        Accepts newly assigned orders, travels up to ``speed`` units along
        streets, and handles arrival at restaurants (pickup) and customers
        (delivery) along the way. Every state change is logged.
        """
        self._sync_assignments()
        budget = self.speed
        while True:
            order = self.current_order()
            if order is None:
                break
            target = order.res_pos if order.status == ORDER_ASSIGNED else order.cus_pos
            if self.position == target:
                self._arrive(order)
                continue
            if budget <= 0:
                break
            waypoint, special = PathPlanner.next_waypoint(self.position, target)
            self.special_case = special
            if waypoint == self.position:
                break
            budget = self._travel(waypoint, budget)
        self.state = self._derive_state()

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------
    def _derive_state(self) -> int:
        """Compute the rider state from its active orders."""
        active = self.active_orders()
        if not active:
            return STATE_IDLE
        if active[0].status == ORDER_PICKED_UP:
            return STATE_DELIVERING
        return STATE_PICKING_UP

    def _sync_assignments(self) -> None:
        """Log an "accepted_order" event for each newly assigned order."""
        for order in self.orders:
            if order.status in (ORDER_ASSIGNED, ORDER_PICKED_UP, ORDER_COMPLETED):
                if order.id not in self._accepted_ids:
                    self._accepted_ids.add(order.id)
                    self.state = self._derive_state()
                    self._record(EVENT_ACCEPTED, order.id)

    def _arrive(self, order: Any) -> None:
        """Handle arrival at the restaurant or the customer location."""
        if order.status == ORDER_ASSIGNED:
            order.mark_picked_up(globalvar.current_tick())
            self.state = self._derive_state()
            self._record(EVENT_ARRIVED, order.id)
        else:
            order.complete(globalvar.current_tick())
            self.state = self._derive_state()
            self._record(EVENT_DELIVERED, order.id)

    def _travel(self, waypoint: Point, budget: int) -> int:
        """Move along a single axis toward ``waypoint`` using the budget.

        Returns:
            The remaining movement budget.
        """
        dx = waypoint[0] - self.x
        dy = waypoint[1] - self.y
        if dx and dy:
            raise ValueError("Waypoint must be axis-aligned with the rider.")
        distance = abs(dx) + abs(dy)
        step = min(distance, budget)
        if dx:
            self.x += _sign(dx) * step
        else:
            self.y += _sign(dy) * step
        return budget - step

    def _record(self, event: str, order_id: Optional[int]) -> None:
        """Append a status-change entry to the rider log."""
        entry = {
            "time": globalvar.current_tick(),
            "event": event,
            "order_id": order_id,
            "rider_id": self.rider_id,
            "x": self.x,
            "y": self.y,
            "state": self.state,
        }
        self.log.append(entry)
        logger.info(
            "tick=%s rider=%s event=%s order=%s pos=(%s,%s) state=%s",
            entry["time"],
            self.rider_id,
            event,
            order_id,
            self.x,
            self.y,
            self.state,
        )

    def to_dict(self) -> Dict[str, Any]:
        """Return a JSON-serialisable representation of the rider."""
        return {
            "rider_id": self.rider_id,
            "x": self.x,
            "y": self.y,
            "speed": self.speed,
            "state": self.state,
            "special_case": self.special_case,
            "order_ids": [o.id for o in self.orders],
        }
