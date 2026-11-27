"""Rider model: state, orders, movement and event logging.

A rider starts idle (state 0). When an order is assigned by appending it to
``rider.orders``, the next call to ``move()`` moves the rider to picking up
(state 1) and logs ``accepted_order``. On reaching the restaurant the rider
enters delivering (state 2) and logs ``arrived_at_merchant``. On reaching the
customer the order is completed, the rider returns to idle (state 0), and
``delivered_to_customer`` is logged.
"""

import logging
from collections import deque
from typing import Any, Deque, Dict, List, Optional, Tuple

import globalvar
import order_model
from order_model import Order
from pathplanner import PathPlanner, RoutePoint

logger = logging.getLogger(__name__)

IDLE = 0
PICKING_UP = 1
DELIVERING = 2
STATE_NAMES = {IDLE: "idle", PICKING_UP: "picking up", DELIVERING: "delivering"}

MERCHANT_TAG = "merchant"
CUSTOMER_TAG = "customer"

SPAWN_X = 50
SPAWN_Y = 50
DEFAULT_SPEED = 100


class Rider:
    """A delivery rider that moves on the street grid and serves orders."""

    def __init__(self, rider_id: int, x: int = SPAWN_X, y: int = SPAWN_Y,
                 speed: int = DEFAULT_SPEED) -> None:
        """Create a rider and log its spawn.

        Args:
            rider_id: Unique rider identifier.
            x: Initial x coordinate (0-800).
            y: Initial y coordinate (0-800).
            speed: Movement speed in units per tick (must be positive).

        Raises:
            ValueError: If speed is not positive.
        """
        if speed <= 0:
            raise ValueError("rider speed must be positive")
        self.rider_id: int = rider_id
        self.x: int = x
        self.y: int = y
        self.speed: int = speed
        self.state: int = IDLE
        self.orders: List[Order] = []
        self.special_case: bool = False
        self.route: Deque[RoutePoint] = deque()
        self.current_order: Optional[Order] = None
        self.total_distance: int = 0
        self.log: List[Dict[str, Any]] = []
        self._planner = PathPlanner()
        self._record("spawn", None)

    # ------------------------------------------------------------------ helpers
    def position(self) -> Tuple[int, int]:
        """Return the current position ``(x, y)``."""
        return self.x, self.y

    def state_name(self) -> str:
        """Return a human-readable name for the current state."""
        return STATE_NAMES.get(self.state, "unknown")

    def planned_points(self) -> List[Tuple[int, int]]:
        """Return the remaining route as a list of ``(x, y)`` points."""
        return [(px, py) for px, py, _ in self.route]

    def _tick(self) -> int:
        """Return the current simulated tick."""
        return globalvar.get_value("tick", 0) or 0

    def _record(self, event: str, order_id: Optional[int]) -> None:
        """Append a status-change entry to the rider log.

        Args:
            event: Event name (spawn, accepted_order, arrived_at_merchant,
                delivered_to_customer).
            order_id: Related order identifier, or None.
        """
        entry = {
            "event": event,
            "order_id": order_id,
            "tick": self._tick(),
            "x": self.x,
            "y": self.y,
            "state": self.state,
        }
        self.log.append(entry)
        logger.info("Rider %s %s order=%s at (%s,%s)",
                    self.rider_id, event, order_id, self.x, self.y)

    def reset_to_idle(self) -> None:
        """Force the rider back to idle and clear any active route.

        Used by the system consistency check to recover from inconsistent
        states.
        """
        self.state = IDLE
        self.route.clear()
        self.current_order = None
        self.special_case = False

    # ------------------------------------------------------------ order flow
    def _start_order(self, order: Order) -> None:
        """Begin picking up an order (idle -> picking up).

        Builds a multi-destination route: current position to the restaurant,
        then restaurant to the customer.

        Args:
            order: The order to start.
        """
        self.current_order = order
        self.state = PICKING_UP
        order.set_status(order_model.STATUS_PICKING_UP)
        rx, ry = order.res_center
        cx, cy = order.cus_center
        stops = [(rx, ry, MERCHANT_TAG), (cx, cy, CUSTOMER_TAG)]
        self.route = deque(self._planner.plan_route((self.x, self.y), stops))
        # Special case: restaurant directly above/below/left/right of the rider.
        self.special_case = self.x == rx or self.y == ry
        self._record("accepted_order", order.id)

    def _arrive(self, tag: Optional[str]) -> None:
        """Handle reaching a route point that carries a stop tag.

        Args:
            tag: Stop tag of the reached point, or None.
        """
        order = self.current_order
        if order is None:
            return
        if tag == MERCHANT_TAG:
            self.state = DELIVERING
            order.set_status(order_model.STATUS_DELIVERING)
            self._record("arrived_at_merchant", order.id)
        elif tag == CUSTOMER_TAG:
            self._complete_current_order()

    def _complete_current_order(self) -> None:
        """Finish the active order, release the rider and charge fuel cost."""
        order = self.current_order
        if order is None:
            return
        order.complete(self._tick())
        if order in self.orders:
            self.orders.remove(order)
        params = globalvar.get_value("params", {}) or {}
        divisor = params.get("fuel_divisor", 10)
        fuel_cost = order.distance // divisor
        globalvar.set_value("funds", globalvar.get_value("funds", 0) - fuel_cost)
        self.reset_to_idle()
        self._record("delivered_to_customer", order.id)

    # --------------------------------------------------------------- movement
    def move(self) -> None:
        """Advance the rider by one tick.

        Handles the idle -> picking up transition for newly assigned orders,
        moves along the street route using at most ``speed`` units, and logs
        state transitions when merchant or customer stops are reached.
        """
        if not self.orders:
            if self.state != IDLE or self.route:
                self.reset_to_idle()
            return

        if self.current_order is None:
            self._start_order(self.orders[0])

        budget = self.speed
        while budget > 0 and self.route:
            tx, ty, tag = self.route[0]
            dx = tx - self.x
            dy = ty - self.y
            if dx == 0 and dy == 0:
                self.route.popleft()
                self._arrive(tag)
                continue
            step = min(budget, abs(dx) + abs(dy))
            move_x = min(abs(dx), step)
            move_y = min(abs(dy), step - move_x)
            self.x += move_x if dx >= 0 else -move_x
            self.y += move_y if dy >= 0 else -move_y
            moved = move_x + move_y
            budget -= moved
            self.total_distance += moved
            if self.current_order is not None:
                self.current_order.distance += moved

    # ------------------------------------------------------------ serialise
    def to_dict(self) -> Dict[str, Any]:
        """Return a JSON-serialisable representation of the rider.

        Returns:
            Dictionary with rider attributes and its event log.
        """
        return {
            "rider_id": self.rider_id,
            "x": self.x,
            "y": self.y,
            "speed": self.speed,
            "state": self.state,
            "state_name": self.state_name(),
            "orders": [order.id for order in self.orders],
            "special_case": self.special_case,
            "total_distance": self.total_distance,
            "log": list(self.log),
        }

    def __repr__(self) -> str:
        return f"Rider(id={self.rider_id}, pos=({self.x},{self.y}), state={self.state})"
