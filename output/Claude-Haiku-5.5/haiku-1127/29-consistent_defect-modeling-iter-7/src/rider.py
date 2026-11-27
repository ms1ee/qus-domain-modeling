"""Rider model: state machine, movement and delivery log.

Rider states:
    0 - Idle (available for new orders)
    1 - Picking up (en route to the restaurant)
    2 - Delivering (en route to the customer)

State transitions:
    Idle (0) -> Picking up (1)    when an assigned order is accepted
    Picking up (1) -> Delivering (2)  on arrival at the restaurant
    Delivering (2) -> Picking up (1)  after delivery, if more orders wait
    Delivering (2) -> Idle (0)        after delivery, if no orders wait
"""

import logging
from typing import Any, Dict, List, Optional, Tuple

import globalvar
from order_model import ACTIVE_STATUSES
from path_planner import PathPlanner

logger = logging.getLogger(__name__)

STATE_IDLE = 0
STATE_PICKING_UP = 1
STATE_DELIVERING = 2

STATE_NAMES = {
    STATE_IDLE: "idle",
    STATE_PICKING_UP: "picking up",
    STATE_DELIVERING: "delivering",
}

RIDER_SPEED = 20
START_X = 400
START_Y = 400

_planner = PathPlanner()


class Rider:
    """A delivery rider that moves along streets and serves orders.

    Attributes:
        rider_id: Unique identifier.
        x: Current x coordinate.
        y: Current y coordinate.
        speed: Movement speed in units per tick.
        state: Current state (0 idle, 1 picking up, 2 delivering).
        orders: All orders ever assigned to this rider (history included).
        special_case: Flag set while moving in a straight line to the target.
        log: Chronological list of event dictionaries. Each entry contains
            "event" and "order_id" plus "tick", "rider_id", "x", "y", "state".
    """

    def __init__(self, rider_id: int) -> None:
        """Create a rider at the default start position (400, 400).

        Args:
            rider_id: Unique identifier for the rider.
        """
        self.rider_id: int = int(rider_id)
        self.x: int = START_X
        self.y: int = START_Y
        self.speed: int = RIDER_SPEED
        self.state: int = STATE_IDLE
        self.orders: List[Any] = []
        self.special_case: bool = False
        self.log: List[Dict[str, Any]] = []
        self._record("spawn", None)

    @property
    def position(self) -> Tuple[int, int]:
        """Current location as a tuple."""
        return (self.x, self.y)

    @property
    def state_name(self) -> str:
        """Human-readable state name."""
        return STATE_NAMES.get(self.state, "unknown")

    def current_order(self) -> Optional[Any]:
        """Return the order currently being served, or None.

        The first active order in the rider's list is always the one being
        served, so orders are handled in assignment sequence.
        """
        for order in self.orders:
            if order.status in ACTIVE_STATUSES:
                return order
        return None

    def active_order_count(self) -> int:
        """Return how many assigned orders are not yet delivered."""
        return sum(1 for order in self.orders if order.status in ACTIVE_STATUSES)

    def move(self) -> None:
        """Advance the rider by one tick.

        State transitions and their log entries happen here. The rider
        spends its speed budget walking along streets toward the current
        target. Arrival at a restaurant or customer is processed immediately,
        and any leftover budget is spent heading to the next target.
        """
        now = self._now()
        self.special_case = False

        if self.state == STATE_IDLE:
            order = self.current_order()
            if order is None:
                return
            self.state = STATE_PICKING_UP
            self._record("accepted_order", order.id)

        budget = self.speed
        while budget > 0:
            order = self.current_order()
            if order is None:
                self._become_idle()
                break
            tx, ty = self._target_for(order)
            if (self.x, self.y) == (tx, ty):
                self._arrive(order, now)
                continue
            self.special_case = (self.x == tx or self.y == ty)
            nx, ny, used = _planner.next_step(self.x, self.y, tx, ty, budget)
            if used <= 0:
                break
            self.x, self.y = nx, ny
            budget -= used

    def _target_for(self, order: Any) -> Tuple[int, int]:
        """Return the current destination for the given order."""
        if self.state == STATE_PICKING_UP:
            return order.restaurant_pos
        return order.customer_pos

    def _arrive(self, order: Any, now: int) -> None:
        """Process arrival at the current destination.

        Args:
            order: The order being served.
            now: The current tick.
        """
        if self.state == STATE_PICKING_UP:
            order.mark_picked_up()
            self.state = STATE_DELIVERING
            self._record("arrived_at_merchant", order.id)
        elif self.state == STATE_DELIVERING:
            order.mark_completed(now)
            self._record("delivered_to_customer", order.id)
            next_order = self.current_order()
            if next_order is not None:
                self.state = STATE_PICKING_UP
                self._record("accepted_order", next_order.id)
            else:
                self._become_idle()

    def _become_idle(self) -> None:
        """Release the rider so it can take new orders."""
        self.state = STATE_IDLE
        self.special_case = False

    def _now(self) -> int:
        """Return the current simulation tick."""
        return int(globalvar.get_value("current_tick", 0) or 0)

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
            "tick": self._now(),
            "rider_id": self.rider_id,
            "x": self.x,
            "y": self.y,
            "state": self.state,
        }
        self.log.append(entry)
        logger.debug("Rider %d: %s (order %s)", self.rider_id, event, order_id)
