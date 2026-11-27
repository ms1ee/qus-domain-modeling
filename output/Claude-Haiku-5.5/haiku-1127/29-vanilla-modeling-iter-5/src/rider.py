"""Rider model: state machine, movement and order execution.

Rider states:
    0 idle, 1 picking up (en route to restaurant), 2 delivering (en route to customer).

Log events recorded in ``Rider.log``:
    "spawn", "accepted_order", "arrived_at_merchant", "delivered_to_customer".
"""

import logging
from typing import TYPE_CHECKING, Any, Dict, List, Optional, Tuple

import config
import globalvar
from path_planner import PathPlanner

if TYPE_CHECKING:  # pragma: no cover
    from order_model import Order

logger = logging.getLogger(__name__)

STATE_IDLE = 0
STATE_PICKING_UP = 1
STATE_DELIVERING = 2
STATE_NAMES = {
    STATE_IDLE: "idle",
    STATE_PICKING_UP: "picking up",
    STATE_DELIVERING: "delivering",
}

LOG_LIMIT = 2000
Point = Tuple[int, int]


def _current_tick() -> int:
    """Return the current simulation tick from the global store.

    Returns:
        The tick counter, or 0 if it has not been set.
    """
    value = globalvar.get_value("current_tick")
    return int(value) if value is not None else 0


class Rider:
    """A delivery rider.

    Attributes:
        rider_id: Unique identifier.
        x: Current X coordinate.
        y: Current Y coordinate.
        speed: Movement speed in units per tick.
        state: Current status enum (0, 1 or 2).
        orders: Assigned orders; the first element is the active order.
        special_case: Flag set while aligned with the current target.
        log: Status change history (list of dictionaries).
        route: Remaining waypoints for the current leg.
    """

    def __init__(self, rider_id: int) -> None:
        """Create a rider at the configured start position in idle state.

        Args:
            rider_id: Unique rider identifier.
        """
        self.rider_id: int = int(rider_id)
        self.x: int = int(config.CONFIG["rider_start_x"])
        self.y: int = int(config.CONFIG["rider_start_y"])
        self.speed: int = int(config.CONFIG["rider_speed"])
        self.state: int = STATE_IDLE
        self.orders: List["Order"] = []
        self.special_case: bool = False
        self.log: List[Dict[str, Any]] = []
        self.route: List[Point] = []
        self._route_goal: Optional[Point] = None
        self._planner = PathPlanner()
        self._record("spawn", None)

    def _record(self, event: str, order_id: Optional[int]) -> None:
        """Append an entry to the rider's status log.

        Args:
            event: Event name.
            order_id: Related order identifier, or None.
        """
        entry = {
            "event": event,
            "order_id": order_id,
            "tick": _current_tick(),
            "rider_id": self.rider_id,
            "x": self.x,
            "y": self.y,
            "state": self.state,
        }
        self.log.append(entry)
        if len(self.log) > LOG_LIMIT:
            del self.log[: len(self.log) - LOG_LIMIT]
        logger.debug("rider %s: %s (order %s)", self.rider_id, event, order_id)

    def reset_route(self) -> None:
        """Discard the planned route so that it is recomputed on the next move."""
        self.route = []
        self._route_goal = None

    def current_target(self) -> Optional[Point]:
        """Return the active destination.

        Returns:
            Restaurant point while picking up, customer point while delivering,
            restaurant point when idle with orders, or None without orders.
        """
        if not self.orders:
            return None
        order = self.orders[0]
        if self.state == STATE_DELIVERING:
            return order.cus_pos
        return order.res_pos

    def move(self) -> None:
        """Advance the rider by one tick.

        Handles the state transitions:
            idle -> picking up when an order is present,
            picking up -> delivering on arrival at the restaurant,
            delivering -> idle on delivery to the customer.
        """
        if not self.orders:
            if self.state != STATE_IDLE:
                self.state = STATE_IDLE
            self.reset_route()
            self.special_case = False
            return

        order = self.orders[0]
        if self.state == STATE_IDLE:
            self.state = STATE_PICKING_UP
            self.reset_route()
            self._record("accepted_order", order.id)

        target = self.current_target()
        if target is None:  # pragma: no cover - guarded above
            return
        if self._route_goal != target:
            self.route = self._planner.plan((self.x, self.y), target)
            self._route_goal = target

        self.x, self.y, self.route = self._planner.step(
            self.x, self.y, self.route, self.speed
        )
        self.special_case = self.x == target[0] or self.y == target[1]
        if self.route:
            return

        if self.state == STATE_PICKING_UP:
            self.state = STATE_DELIVERING
            self.reset_route()
            self._record("arrived_at_merchant", order.id)
        elif self.state == STATE_DELIVERING:
            order.mark_completed(_current_tick())
            if order in self.orders:
                self.orders.remove(order)
            self.state = STATE_IDLE
            self.reset_route()
            self.special_case = False
            self._record("delivered_to_customer", order.id)

    def to_dict(self) -> Dict[str, Any]:
        """Return a JSON-serialisable representation of the rider.

        Returns:
            Dictionary with the rider's attributes and assigned order ids.
        """
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
