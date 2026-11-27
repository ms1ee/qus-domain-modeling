"""Rider model: movement, state transitions and event logging.

Rider states:
    0 - idle
    1 - picking up (en route to the restaurant)
    2 - delivering (en route to the customer)
"""

import logging
from typing import TYPE_CHECKING, Any, Dict, List, Optional, Tuple

from config import (
    MAX_WAIT_TICKS,
    RIDER_SPAWN_X,
    RIDER_SPAWN_Y,
    RIDER_SPEED,
    STATE_DELIVERING,
    STATE_IDLE,
    STATE_PICKING_UP,
)
from globalvar import get_value
from path_planner import PathPlanner

if TYPE_CHECKING:  # pragma: no cover
    from order_model import Order

logger = logging.getLogger(__name__)

Point = Tuple[int, int]


class Rider:
    """A delivery rider that serves one or more orders.

    Attributes:
        rider_id: Unique identifier.
        x: Current x coordinate.
        y: Current y coordinate.
        speed: Units moved per tick.
        state: Current state (0 idle, 1 picking up, 2 delivering).
        orders: Assigned orders; index 0 is the order currently served.
        special_case: True while the rider is aligned with its target and
            moves in a straight line.
        log: Chronological list of event dictionaries with keys ``event``
            and ``order_id`` plus ``time``, ``x``, ``y``, ``state``, ``orders``.
        total_distance: Total distance travelled in coordinate units.
    """

    def __init__(self, rider_id: int) -> None:
        """Create a rider at the spawn location in the idle state.

        Args:
            rider_id: Unique identifier assigned by the system.
        """
        self.rider_id: int = rider_id
        self.x: int = RIDER_SPAWN_X
        self.y: int = RIDER_SPAWN_Y
        self.speed: int = RIDER_SPEED
        self.state: int = STATE_IDLE
        self.orders: List["Order"] = []
        self.special_case: bool = False
        self.log: List[Dict[str, Any]] = []
        self.total_distance: int = 0
        self._wait_ticks: int = 0
        self._planner = PathPlanner()
        self._record("spawn", None)

    # ------------------------------------------------------------------
    # Properties and helpers
    # ------------------------------------------------------------------
    @property
    def position(self) -> Point:
        """Current ``(x, y)`` position."""
        return (self.x, self.y)

    @property
    def current_order(self) -> Optional["Order"]:
        """The order currently being served, or None."""
        return self.orders[0] if self.orders else None

    def _now(self) -> int:
        """Return the current simulated tick."""
        return int(get_value("time", 0))

    def _record(self, event: str, order_id: Optional[int]) -> None:
        """Append an event entry to the rider log."""
        self.log.append({
            "event": event,
            "order_id": order_id,
            "time": self._now(),
            "x": self.x,
            "y": self.y,
            "state": self.state,
            "orders": [order.id for order in self.orders],
        })

    def _become_idle(self) -> None:
        """Release the rider so it can accept new orders."""
        self.state = STATE_IDLE
        self.special_case = False
        self._wait_ticks = 0

    def _current_target(self) -> Point:
        """Return the coordinate the rider is currently heading to."""
        order = self.current_order
        if order is None:
            return self.position
        if self.state == STATE_PICKING_UP:
            return order.res_pos
        return order.cus_pos

    def _is_occupied(self, point: Point) -> bool:
        """Return True if another active rider occupies ``point``."""
        for other in get_value("riders") or []:
            if other is self:
                continue
            if other.state != STATE_IDLE and other.position == point:
                return True
        return False

    # ------------------------------------------------------------------
    # Order handling
    # ------------------------------------------------------------------
    def accept_order(self, order: "Order") -> None:
        """Assign an order to this rider.

        The order is appended to ``orders``; an idle rider moves to the
        picking-up state.

        Args:
            order: The order to assign.
        """
        self.orders.append(order)
        order.assign_to(self.rider_id)
        if self.state == STATE_IDLE:
            self.state = STATE_PICKING_UP
        self._record("accepted_order", order.id)

    def _arrive_at_merchant(self, order: "Order") -> None:
        """Handle arrival at the restaurant: switch to delivering."""
        self.state = STATE_DELIVERING
        self.special_case = False
        order.mark_picked_up(self._now())
        self._record("arrived_at_merchant", order.id)

    def _deliver(self, order: "Order") -> None:
        """Handle delivery to the customer and release the order."""
        order.mark_completed(self._now())
        self.orders.pop(0)
        self._record("delivered_to_customer", order.id)
        if self.orders:
            self.state = STATE_PICKING_UP
            self.special_case = False
        else:
            self._become_idle()

    def _check_arrival(self) -> bool:
        """Process arrival at the current target.

        Returns:
            True if an arrival event was handled.
        """
        order = self.current_order
        if order is None:
            return False
        if self.state == STATE_PICKING_UP and self.position == order.res_pos:
            self._arrive_at_merchant(order)
            return True
        if self.state == STATE_DELIVERING and self.position == order.cus_pos:
            self._deliver(order)
            return True
        return False

    # ------------------------------------------------------------------
    # Movement
    # ------------------------------------------------------------------
    def move(self) -> None:
        """Advance the rider by one tick.

        Moves up to ``speed`` units along the street grid towards the current
        target, handles arrival at the restaurant and at the customer, and
        waits a limited number of ticks when the next cell is occupied to
        avoid conflicts and deadlocks.
        """
        if not self.orders:
            if self.state != STATE_IDLE:
                self._become_idle()
            return
        if self.state == STATE_IDLE:
            self.state = STATE_PICKING_UP

        if self._check_arrival():
            return

        target = self._current_target()
        self.special_case = self.x == target[0] or self.y == target[1]
        new_pos = self._planner.next_position(self.position, target, self.speed)

        if new_pos != self.position:
            if self._is_occupied(new_pos) and self._wait_ticks < MAX_WAIT_TICKS:
                self._wait_ticks += 1
                logger.debug("Rider %s waiting at %s", self.rider_id, self.position)
                return
            self._wait_ticks = 0
            self.total_distance += PathPlanner.manhattan(self.position, new_pos)
            self.x, self.y = new_pos

        self._check_arrival()

    # ------------------------------------------------------------------
    # Serialisation
    # ------------------------------------------------------------------
    def to_dict(self) -> Dict[str, Any]:
        """Return a JSON-serialisable representation of the rider."""
        return {
            "rider_id": self.rider_id,
            "x": self.x,
            "y": self.y,
            "speed": self.speed,
            "state": self.state,
            "special_case": self.special_case,
            "order_ids": [order.id for order in self.orders],
            "total_distance": self.total_distance,
            "log": list(self.log),
        }
