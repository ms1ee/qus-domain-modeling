"""Rider model: state machine, street movement and event logging.

Rider states:
    0 (idle)        - available for new orders.
    1 (picking up)  - driving to the restaurant of the current order.
    2 (delivering)  - driving to the customer of the current order.

Transitions:
    Idle -> Picking Up      on the first tick after an order is assigned.
    Picking Up -> Delivering when the restaurant is reached.
    Delivering -> Idle      when the customer is reached (order completed).
"""

import logging
from typing import Any, Dict, List, Optional, Set

import globalvar
from order_model import ORDER_FEE, Order
from path_planner import PathPlanner, Point

logger = logging.getLogger(__name__)

STATE_IDLE = 0
STATE_PICKING_UP = 1
STATE_DELIVERING = 2
STATE_NAMES = {
    STATE_IDLE: "idle",
    STATE_PICKING_UP: "picking up",
    STATE_DELIVERING: "delivering",
}
DEFAULT_SPEED = 100  # map units per tick


def _current_tick() -> int:
    """Return the current simulated tick from the global store."""
    return int(globalvar.get_value("tick", 0) or 0)


class Rider:
    """A delivery rider moving along the street grid.

    Attributes:
        rider_id: Unique identifier.
        x, y: Current position (integers, on a street).
        speed: Movement speed in map units per tick.
        state: Current state (0=idle, 1=picking up, 2=delivering).
        orders: Assigned orders; the first entry is the active order.
        special_case: True while moving straight towards a target that is
            directly above/below or on the same street row.
        log: Event records with keys "event", "order_id", "tick", etc.
    """

    def __init__(
        self,
        rider_id: int,
        speed: int = DEFAULT_SPEED,
        start: Optional[Point] = None,
    ) -> None:
        """Create a rider on a street intersection.

        Args:
            rider_id: Unique identifier.
            speed: Movement speed (units/tick), must be positive.
            start: Optional starting intersection. A random one is chosen if
                omitted.

        Raises:
            ValueError: If the speed is not positive or the start point is not
                an intersection.
        """
        if start is None:
            start = PathPlanner.random_node()
        x, y = int(start[0]), int(start[1])
        if not PathPlanner.is_intersection(x, y):
            raise ValueError("riders must start at a street intersection")
        if int(speed) <= 0:
            raise ValueError("rider speed must be positive")

        self.rider_id = int(rider_id)
        self.x = x
        self.y = y
        self.speed = int(speed)
        self.state = STATE_IDLE
        self.orders: List[Order] = []
        self.special_case = False
        self.log: List[Dict[str, Any]] = []
        self._route: Optional[List[Point]] = None
        self._accepted_ids: Set[int] = set()
        self._record("spawn", None)
        logger.info("Rider %d spawned at (%d, %d)", self.rider_id, self.x, self.y)

    # ------------------------------------------------------------------ #
    # Properties and bookkeeping
    # ------------------------------------------------------------------ #
    @property
    def position(self) -> Point:
        """Return the current ``(x, y)`` position."""
        return (self.x, self.y)

    @property
    def state_name(self) -> str:
        """Return a human readable name for the current state."""
        return STATE_NAMES.get(self.state, "unknown")

    def _record(self, event: str, order_id: Optional[int]) -> None:
        """Append an event record to :attr:`log`."""
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
        logger.debug("Rider %d event=%s order=%s", self.rider_id, event, order_id)

    def to_dict(self) -> Dict[str, Any]:
        """Return a JSON-serialisable representation of the rider."""
        return {
            "rider_id": self.rider_id,
            "x": self.x,
            "y": self.y,
            "speed": self.speed,
            "state": self.state,
            "orders": [order.id for order in self.orders],
            "special_case": self.special_case,
        }

    def recover(self) -> None:
        """Reset transient movement state after an inconsistency or error.

        The rider keeps its assigned orders and returns to idle so that the
        active order is restarted cleanly on the next tick.
        """
        logger.warning("Recovering rider %d to idle state", self.rider_id)
        self.state = STATE_IDLE
        self._route = None
        self.special_case = False

    # ------------------------------------------------------------------ #
    # Movement
    # ------------------------------------------------------------------ #
    def move(self) -> None:
        """Advance the rider by one tick.

        Handles order acceptance logging, the idle -> picking-up transition,
        movement along the planned route, and arrival events.
        """
        self._accept_new_orders()

        if self.state == STATE_IDLE:
            if not self.orders:
                return
            self.state = STATE_PICKING_UP
            self._route = None
            self.special_case = False

        if self.state in (STATE_PICKING_UP, STATE_DELIVERING):
            self._advance_leg()

    def _accept_new_orders(self) -> None:
        """Log an ``accepted_order`` event for every newly assigned order."""
        for order in self.orders:
            if order.id not in self._accepted_ids:
                self._accepted_ids.add(order.id)
                self._record("accepted_order", order.id)

    def _advance_leg(self) -> None:
        """Move towards the target of the current leg (restaurant or customer)."""
        if not self.orders:
            logger.warning("Rider %d in state %d without orders", self.rider_id, self.state)
            self.recover()
            return

        order = self.orders[0]
        target = order.res_pos if self.state == STATE_PICKING_UP else order.cus_pos

        if self._route is None:
            self._route = PathPlanner.plan(self.position, target)
            self.special_case = PathPlanner.is_aligned(self.position, target)

        self._travel(self.speed)

        if not self._route:
            self._arrive(order)

    def _travel(self, distance: int) -> None:
        """Move along the remaining route by at most ``distance`` units.

        Movement is axis-aligned: the rider moves along the current street
        towards the next waypoint, consuming waypoints as they are reached.
        """
        remaining = distance
        while remaining > 0 and self._route:
            tx, ty = self._route[0]
            dx = tx - self.x
            dy = ty - self.y
            dist = abs(dx) + abs(dy)
            if dist <= remaining:
                self.x, self.y = tx, ty
                self._route.pop(0)
                remaining -= dist
            else:
                if dx != 0:
                    self.x += remaining if dx > 0 else -remaining
                else:
                    self.y += remaining if dy > 0 else -remaining
                remaining = 0

    def _arrive(self, order: Order) -> None:
        """Handle arrival at the target of the current leg."""
        if self.state == STATE_PICKING_UP:
            self._record("arrived_at_merchant", order.id)
            self.state = STATE_DELIVERING
            self._route = None
            self.special_case = False
            return

        order.mark_completed(_current_tick())
        self.orders.remove(order)
        self._accepted_ids.discard(order.id)
        funds = int(globalvar.get_value("funds", 0) or 0)
        globalvar.set_value("funds", funds + ORDER_FEE)
        self._record("delivered_to_customer", order.id)
        self.state = STATE_IDLE
        self._route = None
        self.special_case = False
