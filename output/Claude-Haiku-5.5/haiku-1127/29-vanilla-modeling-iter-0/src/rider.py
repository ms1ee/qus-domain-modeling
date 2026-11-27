"""Rider model: state machine, street-based movement and event logging.

Rider state machine:
    Idle (0) -> Picking Up (1) when an order is accepted,
    Picking Up (1) -> Delivering (2) on arrival at the restaurant,
    Delivering (2) -> Idle (0) (or Picking Up for the next order)
    on delivery to the customer.
"""

import logging
from collections import deque
from typing import Any, Deque, Dict, List, Optional, Tuple

import globalvar
from path_planner import DEFAULT_PLANNER

LOGGER = logging.getLogger("dispatch.rider")

STATE_IDLE = 0
STATE_PICKING_UP = 1
STATE_DELIVERING = 2
STATE_LABELS = {
    STATE_IDLE: "idle",
    STATE_PICKING_UP: "picking up",
    STATE_DELIVERING: "delivering",
}

DEFAULT_X = 435
DEFAULT_Y = 385
DEFAULT_SPEED = 10
MAX_LOG_ENTRIES = 1000
MAX_PATH_POINTS = 2000
MAX_CONFLICT_WAITS = 3


class Rider:
    """A delivery rider that moves along streets and serves orders.

    Attributes:
        rider_id: Unique identifier.
        x: Current x coordinate.
        y: Current y coordinate.
        speed: Movement speed in units per tick.
        state: 0 = idle, 1 = picking up, 2 = delivering.
        orders: Assigned orders; the first element is the active order.
        special_case: True while the rider is directly above or below its
            current target.
        log: Event entries with keys "event", "order_id", "time", etc.
        path_history: Recent (time, x, y) positions for route display.
    """

    def __init__(self, rider_id: int) -> None:
        """Create a rider at the default start position.

        Args:
            rider_id: Unique integer identifier.

        Raises:
            TypeError: If rider_id is not an integer.
        """
        if isinstance(rider_id, bool) or not isinstance(rider_id, int):
            raise TypeError("rider_id must be an integer")
        self.rider_id = rider_id
        self.x = DEFAULT_X
        self.y = DEFAULT_Y
        self.speed = DEFAULT_SPEED
        self.state = STATE_IDLE
        self.orders: List[Any] = []
        self.special_case = False
        self.log: List[Dict[str, Any]] = []
        self.path_history: Deque[Tuple[int, int, int]] = deque(
            maxlen=MAX_PATH_POINTS)
        self._wait_ticks = 0
        self._record_position()
        self._add_log("spawn", None)

    @property
    def position(self) -> Tuple[int, int]:
        """Current (x, y) position."""
        return self.x, self.y

    @property
    def state_label(self) -> str:
        """Human-readable state name."""
        return STATE_LABELS.get(self.state, "unknown")

    def is_idle(self) -> bool:
        """Return True when the rider has no state and no assigned orders."""
        return self.state == STATE_IDLE and not self.orders

    def current_order(self) -> Optional[Any]:
        """Return the active order (first in the list), or None."""
        return self.orders[0] if self.orders else None

    def accept_order(self, order: Any) -> None:
        """Append an order to this rider's list and mark it assigned.

        Args:
            order: The Order to assign.
        """
        self.orders.append(order)
        order.assign_to(self.rider_id)

    def move(self) -> None:
        """Advance the rider by one tick.

        Handles state transitions and their log entries. Movement is limited
        to ``speed`` units along street-preferring routes.
        """
        order = self.current_order()
        if order is None:
            if self.state != STATE_IDLE:
                LOGGER.warning("Rider %d had state %d without orders; "
                               "resetting to idle", self.rider_id, self.state)
                self.state = STATE_IDLE
            self.special_case = False
            self._wait_ticks = 0
            return

        if self.state == STATE_IDLE:
            self.state = STATE_PICKING_UP
            self._add_log("accepted_order", order.id)

        if self.state == STATE_PICKING_UP:
            tx, ty = order.restaurant_pos
            self._travel_to(tx, ty)
            if self.position == (tx, ty):
                self._arrive_at_merchant(order)
        elif self.state == STATE_DELIVERING:
            tx, ty = order.customer_pos
            self._travel_to(tx, ty)
            if self.position == (tx, ty):
                self._deliver(order)

    def _now(self) -> int:
        """Return the current simulated tick."""
        return int(globalvar.get_value("simulated_time", 0) or 0)

    def _add_log(self, event: str, order_id: Optional[int]) -> None:
        """Append an event entry to the rider log (bounded in size)."""
        entry = {
            "event": event,
            "order_id": order_id,
            "time": self._now(),
            "rider_id": self.rider_id,
            "x": self.x,
            "y": self.y,
            "state": self.state,
        }
        self.log.append(entry)
        overflow = len(self.log) - MAX_LOG_ENTRIES
        if overflow > 0:
            del self.log[:overflow]
        LOGGER.debug("Rider %d event %s order=%s", self.rider_id, event,
                     order_id)

    def _record_position(self) -> None:
        """Record the current position in the bounded path history."""
        self.path_history.append((self._now(), self.x, self.y))

    def _arrive_at_merchant(self, order: Any) -> None:
        """Transition from picking up to delivering."""
        self.state = STATE_DELIVERING
        self.special_case = False
        self._wait_ticks = 0
        self._add_log("arrived_at_merchant", order.id)

    def _deliver(self, order: Any) -> None:
        """Complete the active order and update the rider state."""
        order.complete(self._now())
        self.orders.remove(order)
        self._add_log("delivered_to_customer", order.id)
        self.state = STATE_PICKING_UP if self.orders else STATE_IDLE
        self.special_case = False
        self._wait_ticks = 0

    def _is_occupied(self, x: int, y: int) -> bool:
        """Return True if another rider currently stands at (x, y)."""
        for other in globalvar.get_value("riders", []) or []:
            if other is not self and (other.x, other.y) == (x, y):
                return True
        return False

    def _travel_to(self, tx: int, ty: int) -> None:
        """Move one tick toward (tx, ty) with conflict avoidance.

        If the next cell is occupied by another rider, the rider waits. After
        a wait the alternate route is tried; after MAX_CONFLICT_WAITS waits
        the rider proceeds anyway, which prevents deadlock.
        """
        self.special_case = DEFAULT_PLANNER.is_directly_above_or_below(
            self.x, self.y, tx, ty)
        if self.position == (tx, ty):
            return
        alternate = self._wait_ticks > 0
        nx, ny = DEFAULT_PLANNER.next_position(
            self.x, self.y, tx, ty, self.speed, alternate=alternate)
        if (nx, ny) != (self.x, self.y) and self._is_occupied(nx, ny):
            if self._wait_ticks < MAX_CONFLICT_WAITS:
                self._wait_ticks += 1
                LOGGER.debug("Rider %d waiting for (%d,%d)", self.rider_id,
                             nx, ny)
                return
        self._wait_ticks = 0
        self.x, self.y = nx, ny
        self._record_position()

    def to_dict(self) -> Dict[str, Any]:
        """Return a JSON-serialisable snapshot of the rider."""
        return {
            "rider_id": self.rider_id,
            "x": self.x,
            "y": self.y,
            "speed": self.speed,
            "state": self.state,
            "state_label": self.state_label,
            "special_case": self.special_case,
            "order_ids": [order.id for order in self.orders],
        }
