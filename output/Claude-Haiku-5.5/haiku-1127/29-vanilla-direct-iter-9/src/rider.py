"""Rider model: state machine, grid movement and event logging."""

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

DEFAULT_SPEED = 10
SPAWN_X = 435
SPAWN_Y = 385


class Rider:
    """A delivery rider that moves across the grid and serves orders.

    Attributes:
        rider_id: Unique identifier.
        x, y: Current coordinates.
        speed: Distance covered per tick.
        state: 0 = idle, 1 = picking up, 2 = delivering.
        orders: Assigned orders; ``orders[0]`` is the one being served.
        special_case: True while the rider is aligned with its target on one
            axis (directly above/below or beside it).
        path: Remaining waypoints towards the current target.
        distance_travelled: Total units moved since creation.
        log: Chronological event entries. Each entry is a dict with keys
            "event", "order_id", "time", "rider_id", "x", "y" and "state".
            Events: "spawn", "accepted_order", "arrived_at_merchant",
            "delivered_to_customer".
    """

    def __init__(self, rider_id: int) -> None:
        """Create a rider at the spawn point in the idle state.

        Args:
            rider_id: Unique rider identifier.
        """
        self.rider_id: int = int(rider_id)
        self.x: int = SPAWN_X
        self.y: int = SPAWN_Y
        self.speed: int = DEFAULT_SPEED
        self.state: int = STATE_IDLE
        self.orders: List[Any] = []
        self.special_case: bool = False
        self.path: List[Tuple[int, int]] = []
        self.distance_travelled: int = 0
        self.log: List[Dict[str, Any]] = []
        self._record("spawn", None)
        logger.info("Rider #%d spawned at (%d, %d)", self.rider_id, self.x, self.y)

    # ------------------------------------------------------------------ helpers
    @staticmethod
    def _now() -> int:
        """Return the current simulation tick from the global store."""
        return int(globalvar.get_value("time", 0) or 0)

    def _record(self, event: str, order_id: Optional[int]) -> None:
        """Append an entry to the rider's event log."""
        self.log.append(
            {
                "event": event,
                "order_id": order_id,
                "time": self._now(),
                "rider_id": self.rider_id,
                "x": self.x,
                "y": self.y,
                "state": self.state,
            }
        )

    @property
    def state_name(self) -> str:
        """Human readable state name."""
        return STATE_NAMES.get(self.state, "unknown")

    @property
    def position(self) -> Tuple[int, int]:
        """Current ``(x, y)`` position."""
        return self.x, self.y

    def is_idle(self) -> bool:
        """Return True when the rider is idle and has no queued orders."""
        return self.state == STATE_IDLE and not self.orders

    def _plan_to(self, target: Tuple[int, int]) -> None:
        """Compute the route to ``target`` and update the special-case flag."""
        self.path = PathPlanner.plan((self.x, self.y), target)
        self.special_case = self.x == target[0] or self.y == target[1]

    def _advance(self) -> None:
        """Move up to ``speed`` units along the current path."""
        if not self.path:
            return
        old_x, old_y = self.x, self.y
        (self.x, self.y), self.path = PathPlanner.advance(
            self.x, self.y, self.path, self.speed
        )
        self.distance_travelled += abs(self.x - old_x) + abs(self.y - old_y)

    def _reset_idle(self) -> None:
        """Return the rider to the idle state, releasing its resources."""
        self.state = STATE_IDLE
        self.path = []
        self.special_case = False

    def _complete_current_order(self) -> None:
        """Finish the order being delivered and update the rider state."""
        order = self.orders.pop(0)
        order.complete(self._now())
        self._record("delivered_to_customer", order.id)
        logger.info("Rider #%d delivered order #%d", self.rider_id, order.id)
        if self.orders:
            # Serve the next queued order: head back to its restaurant.
            self.state = STATE_PICKING_UP
            self._plan_to(self.orders[0].res_pos)
        else:
            self._reset_idle()

    # --------------------------------------------------------------- public API
    def move(self) -> None:
        """Advance the rider by one tick.

        Handles all state transitions and their log entries:
            Idle -> Picking Up when an order is assigned ("accepted_order").
            Picking Up -> Delivering on arrival at the restaurant
            ("arrived_at_merchant").
            Delivering -> Idle on delivery ("delivered_to_customer").
        """
        if self.state == STATE_IDLE:
            if not self.orders:
                return
            order = self.orders[0]
            self.state = STATE_PICKING_UP
            self._plan_to(order.res_pos)
            self._record("accepted_order", order.id)
            logger.debug("Rider #%d accepted order #%d", self.rider_id, order.id)

        if self.state == STATE_PICKING_UP:
            if not self.orders:
                logger.warning("Rider #%d picking up without orders; resetting", self.rider_id)
                self._reset_idle()
                return
            self._advance()
            if not self.path:
                order = self.orders[0]
                order.mark_picked_up(self._now())
                self.state = STATE_DELIVERING
                self._plan_to(order.cus_pos)
                self._record("arrived_at_merchant", order.id)
        elif self.state == STATE_DELIVERING:
            if not self.orders:
                logger.warning("Rider #%d delivering without orders; resetting", self.rider_id)
                self._reset_idle()
                return
            self._advance()
            if not self.path:
                self._complete_current_order()

    def to_dict(self) -> Dict[str, Any]:
        """Return a JSON-serialisable snapshot of the rider."""
        return {
            "rider_id": self.rider_id,
            "x": self.x,
            "y": self.y,
            "speed": self.speed,
            "state": self.state,
            "state_name": self.state_name,
            "special_case": self.special_case,
            "orders": [order.id for order in self.orders],
            "distance_travelled": self.distance_travelled,
            "log": list(self.log),
        }
