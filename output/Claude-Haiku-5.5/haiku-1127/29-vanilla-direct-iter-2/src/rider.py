"""Rider model: state machine, movement and order handling."""

import logging
from typing import Any, Dict, List, Optional, Tuple

import globalvar
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

DEFAULT_START_X = 435
DEFAULT_START_Y = 385
DEFAULT_SPEED = 10


class Rider:
    """A delivery rider that moves on the grid and carries orders.

    Attributes:
        rider_id: Unique integer identifier.
        x: Current X coordinate (0-800).
        y: Current Y coordinate (0-800).
        speed: Movement speed in units per tick.
        state: 0 = idle, 1 = picking up, 2 = delivering.
        orders: Assigned orders; ``orders[0]`` is the order being served (FIFO).
        special_case: True while special movement rules apply.
        distance_travelled: Total number of unit steps taken.
        log: Chronological list of status-change entries. Each entry is a dict
            with at least the keys ``"event"`` and ``"order_id"``.
    """

    def __init__(
        self,
        rider_id: int,
        x: int = DEFAULT_START_X,
        y: int = DEFAULT_START_Y,
        speed: int = DEFAULT_SPEED,
    ) -> None:
        """Create a new idle rider and log its spawn event.

        Args:
            rider_id: Unique identifier of the rider.
            x: Initial X coordinate.
            y: Initial Y coordinate.
            speed: Movement speed in units per tick.

        Raises:
            TypeError: If ``rider_id`` is not an integer.
        """
        if isinstance(rider_id, bool) or not isinstance(rider_id, int):
            raise TypeError("rider_id must be an integer")
        self.rider_id: int = rider_id
        self.x: int = int(x)
        self.y: int = int(y)
        self.speed: int = int(speed)
        self.state: int = STATE_IDLE
        self.orders: List[Any] = []
        self.special_case: bool = False
        self.distance_travelled: int = 0
        self.log: List[Dict[str, Any]] = []
        self._record("spawn", None)
        logger.info("Rider #%d spawned at (%d, %d)", self.rider_id, self.x, self.y)

    # ------------------------------------------------------------------ helpers
    @property
    def position(self) -> Tuple[int, int]:
        """Current ``(x, y)`` position."""
        return self.x, self.y

    @property
    def state_name(self) -> str:
        """Human-readable name of the current state."""
        return STATE_NAMES.get(self.state, "unknown")

    def is_idle(self) -> bool:
        """Return True if the rider is available for new orders."""
        return self.state == STATE_IDLE

    @staticmethod
    def _current_tick() -> int:
        """Return the global simulated time."""
        return int(globalvar.get_value("tick", 0) or 0)

    def _record(self, event: str, order_id: Optional[int]) -> None:
        """Append a status-change entry to the rider log.

        Args:
            event: Event name, e.g. ``"accepted_order"``.
            order_id: Related order id, or None.
        """
        self.log.append(
            {
                "event": event,
                "order_id": order_id,
                "tick": self._current_tick(),
                "rider_id": self.rider_id,
                "x": self.x,
                "y": self.y,
                "state": self.state,
            }
        )

    # ------------------------------------------------------------ order intake
    def accept_order(self, order: Any) -> None:
        """Accept an order by appending it to ``orders`` and updating state.

        An idle rider moves to the picking-up state. The order's status is
        updated accordingly and an ``accepted_order`` log entry is written.

        Args:
            order: The ``Order`` instance to accept.
        """
        self.orders.append(order)
        if self.state == STATE_IDLE:
            self.state = STATE_PICKING_UP
            order.status = "picking_up"
        self._record("accepted_order", order.id)
        logger.info("Rider #%d accepted order #%d", self.rider_id, order.id)

    # ---------------------------------------------------------------- movement
    def move(self) -> None:
        """Advance the rider by one tick.

        The rider travels up to ``speed`` unit steps towards the current
        target. Reaching the restaurant switches the rider to the delivering
        state; reaching the customer completes the order.
        """
        if not self.orders:
            if self.state != STATE_IDLE:
                self.state = STATE_IDLE
                self.special_case = False
            return

        if self.state == STATE_IDLE:
            self.state = STATE_PICKING_UP
            self.orders[0].status = "picking_up"

        order = self.orders[0]
        target = order.res_pos if self.state == STATE_PICKING_UP else order.cus_pos
        self._travel_towards(target)

        if self.position == tuple(target):
            if self.state == STATE_PICKING_UP:
                self.state = STATE_DELIVERING
                order.status = "delivering"
                self._record("arrived_at_merchant", order.id)
                logger.info("Rider #%d arrived at merchant for order #%d",
                            self.rider_id, order.id)
            else:
                self._complete(order)

    def _travel_towards(self, target: Tuple[int, int]) -> None:
        """Take up to ``speed`` unit steps along the planned street route.

        Args:
            target: Destination ``(x, y)`` position.
        """
        budget = self.speed
        tx, ty = target
        while budget > 0 and self.position != (tx, ty):
            self.special_case = PathPlanner.is_special_case(self.x, self.y, tx, ty)
            self.x, self.y = PathPlanner.next_step(self.x, self.y, tx, ty)
            self.distance_travelled += 1
            budget -= 1

    def _complete(self, order: Any) -> None:
        """Finish delivery of an order and release it from the rider.

        Args:
            order: The order that was delivered (must be ``orders[0]``).
        """
        order.mark_completed(self._current_tick())
        self.orders.remove(order)
        self._record("delivered_to_customer", order.id)
        self.special_case = False
        if self.orders:
            self.state = STATE_PICKING_UP
            self.orders[0].status = "picking_up"
        else:
            self.state = STATE_IDLE
        logger.info("Rider #%d delivered order #%d", self.rider_id, order.id)

    # ------------------------------------------------------------ serialization
    def to_dict(self) -> Dict[str, Any]:
        """Return a JSON-serializable snapshot of the rider.

        Returns:
            Dictionary with the rider attributes and order ids.
        """
        return {
            "rider_id": self.rider_id,
            "x": self.x,
            "y": self.y,
            "speed": self.speed,
            "state": self.state,
            "special_case": self.special_case,
            "orders": [o.id for o in self.orders],
            "log": list(self.log),
        }
