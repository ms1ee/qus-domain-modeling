"""Rider model: state machine, movement and event logging.

State transitions:
    Idle (0)        -> Picking Up (1) when an assigned order is accepted.
    Picking Up (1)  -> Delivering (2) on arrival at the restaurant.
    Delivering (2)  -> Idle (0) on delivery to the customer.
"""

import logging
from typing import Any, Dict, List, Optional, Set

import globalvar
from path_planner import PathPlanner, Point

IDLE = 0
PICKING_UP = 1
DELIVERING = 2

STATE_NAMES = {
    IDLE: "idle",
    PICKING_UP: "picking up",
    DELIVERING: "delivering",
}

SPAWN_POSITION: Point = (50, 50)
DEFAULT_SPEED = 50

logger = logging.getLogger("dispatch.rider")


class Rider:
    """A delivery rider that moves on the street grid and serves orders.

    Attributes:
        rider_id: Unique identifier.
        x: Current x coordinate (integer, 0-800).
        y: Current y coordinate (integer, 0-800).
        speed: Movement speed in units per tick.
        state: 0 = idle, 1 = picking up, 2 = delivering.
        orders: Assigned orders, served in list order.
        special_case: True while moving straight to a target above/below.
        path: Remaining waypoints for the current leg.
        log: Chronological list of event dictionaries.
    """

    def __init__(self, rider_id: int) -> None:
        """Create an idle rider at the spawn position.

        Args:
            rider_id: Unique identifier assigned by the system.
        """
        config = globalvar.get_value("config") or {}
        self.rider_id: int = int(rider_id)
        self.x: int = SPAWN_POSITION[0]
        self.y: int = SPAWN_POSITION[1]
        self.speed: int = int(config.get("rider_speed", DEFAULT_SPEED))
        self.state: int = IDLE
        self.orders: List[Any] = []
        self.special_case: bool = False
        self.path: List[Point] = []
        self.log: List[Dict[str, Any]] = []
        self._record("spawn", None)

    @property
    def position(self) -> Point:
        """Return the current ``(x, y)`` position."""
        return (self.x, self.y)

    @property
    def state_name(self) -> str:
        """Return a human-readable name for the current state."""
        return STATE_NAMES.get(self.state, "unknown")

    def to_dict(self) -> Dict[str, Any]:
        """Return a JSON-serialisable snapshot of the rider.

        Returns:
            Dictionary with rider attributes; orders are stored as IDs.
        """
        return {
            "rider_id": self.rider_id,
            "x": self.x,
            "y": self.y,
            "speed": self.speed,
            "state": self.state,
            "orders": [order.id for order in self.orders],
            "special_case": self.special_case,
        }

    def move(self) -> None:
        """Advance the rider by one tick.

        Handles order acceptance, movement along the planned path, arrival at
        the restaurant, and delivery to the customer. All state transitions
        and their log entries happen here.
        """
        if self.state == IDLE:
            if not self.orders:
                return
            self._begin_pickup()

        self._advance()

        while not self.path:
            if self.state == PICKING_UP:
                self._arrive_at_merchant()
            elif self.state == DELIVERING:
                self._deliver()
                break
            else:
                break

    def _now(self) -> int:
        """Return the current simulated tick."""
        return int(globalvar.get_value("tick", 0) or 0)

    def _record(self, event: str, order_id: Optional[int]) -> None:
        """Append an event entry to the rider log.

        Args:
            event: One of "spawn", "accepted_order", "arrived_at_merchant",
                "delivered_to_customer".
            order_id: Related order ID, or None.
        """
        entry = {
            "event": event,
            "order_id": order_id,
            "tick": self._now(),
            "rider_id": self.rider_id,
            "state": self.state,
            "x": self.x,
            "y": self.y,
        }
        self.log.append(entry)
        logger.debug("Rider %s: %s (order %s)", self.rider_id, event, order_id)

    def _occupied_by_others(self) -> Set[Point]:
        """Return positions occupied by all other riders."""
        riders = globalvar.get_value("riders", []) or []
        return {rider.position for rider in riders if rider is not self}

    def _plan(self, goal: Point) -> None:
        """Plan the path for the current leg toward ``goal``."""
        self.path = PathPlanner.plan(self.position, goal,
                                     self._occupied_by_others())
        self.special_case = PathPlanner.is_special_case(self.position, goal)

    def _advance(self) -> None:
        """Move along the current path using this rider's speed."""
        if not self.path:
            return
        new_pos, self.path, _ = PathPlanner.step_towards(
            self.position, self.path, self.speed)
        self.x, self.y = new_pos

    def _begin_pickup(self) -> None:
        """Accept the next assigned order and head to the restaurant."""
        order = self.orders[0]
        self.state = PICKING_UP
        order.status = "pickup"
        self._record("accepted_order", order.id)
        self._plan(order.res_pos)

    def _arrive_at_merchant(self) -> None:
        """Handle arrival at the restaurant and head to the customer."""
        order = self.orders[0]
        self.state = DELIVERING
        order.status = "delivering"
        self._record("arrived_at_merchant", order.id)
        self._plan(order.cus_pos)

    def _deliver(self) -> None:
        """Complete the current order and return to idle."""
        order = self.orders.pop(0)
        order.mark_completed(self._now())
        self.state = IDLE
        self.special_case = False
        self.path = []
        self._record("delivered_to_customer", order.id)
