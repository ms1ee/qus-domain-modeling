"""Rider model: state machine, movement and order execution."""

from __future__ import annotations

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

DEFAULT_START: Tuple[int, int] = (435, 385)
DEFAULT_SPEED = 10


class Rider:
    """A delivery rider that moves on the grid and executes orders.

    Attributes:
        rider_id: Unique identifier.
        x, y: Current coordinates.
        speed: Movement speed in units per tick.
        state: 0 = idle, 1 = picking up, 2 = delivering.
        orders: Assigned orders (``Order`` objects).
        special_case: True while moving straight to a directly above/below
            target.
        log: Event records with keys ``event`` and ``order_id`` (plus tick,
            position and state).
    """

    def __init__(self, rider_id: int) -> None:
        """Create a rider at the configured start position (default 435,385).

        Args:
            rider_id: Unique rider identifier.
        """
        start = globalvar.get_value("rider_start") or DEFAULT_START
        self.rider_id: int = int(rider_id)
        self.x: int = int(start[0])
        self.y: int = int(start[1])
        self.speed: int = int(globalvar.get_value("rider_speed") or DEFAULT_SPEED)
        self.state: int = STATE_IDLE
        self.orders: List[Any] = []
        self.special_case: bool = False
        self.route: List[Tuple[int, int]] = []
        self.current_order: Optional[Any] = None
        self._accepted_ids: set = set()
        self.log: List[Dict[str, Any]] = []
        self._record("spawn", None)

    # ------------------------------------------------------------------ #
    # Read-only helpers
    # ------------------------------------------------------------------ #
    @property
    def position(self) -> Tuple[int, int]:
        """Return the current ``(x, y)`` position."""
        return self.x, self.y

    @property
    def state_name(self) -> str:
        """Return a human readable name for the current state."""
        return STATE_NAMES.get(self.state, "unknown")

    def is_idle(self) -> bool:
        """Return True when the rider has no state activity and no orders."""
        return self.state == STATE_IDLE and not self.orders

    # ------------------------------------------------------------------ #
    # Logging
    # ------------------------------------------------------------------ #
    @staticmethod
    def _now() -> int:
        """Return the current simulation tick."""
        return int(globalvar.get_value("current_tick", 0))

    def _record(self, event: str, order_id: Optional[int]) -> None:
        """Append an event entry to the rider log."""
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
        logger.debug("Rider #%d %s order=%s at (%d,%d)",
                     self.rider_id, event, order_id, self.x, self.y)

    # ------------------------------------------------------------------ #
    # Simulation
    # ------------------------------------------------------------------ #
    def move(self) -> None:
        """Advance the rider by one tick.

        Idle riders accept the next assigned order (state 0 -> 1) without
        moving in that tick.  Picking-up riders move towards the restaurant
        and switch to delivering (1 -> 2) on arrival.  Delivering riders move
        to the customer and complete the order (2 -> 0), then immediately
        accept the next queued order if one exists.
        """
        self.special_case = False
        if self.state == STATE_IDLE:
            self._accept_next_order()
            return
        self._advance()

    def _accept_next_order(self) -> bool:
        """Accept the first assigned order that has not been started yet.

        Returns:
            True if an order was accepted.
        """
        for order in self.orders:
            if order.id in self._accepted_ids:
                continue
            self._accepted_ids.add(order.id)
            self.current_order = order
            self.state = STATE_PICKING_UP
            self.route = []
            order.status = "picking_up"
            self._record("accepted_order", order.id)
            return True
        return False

    def _advance(self) -> None:
        """Move one tick along the current leg and handle arrivals."""
        order = self.current_order
        if order is None:
            logger.warning("Rider #%d is busy without an order; resetting.", self.rider_id)
            self.state = STATE_IDLE
            self.route = []
            return

        target = order.res_pos if self.state == STATE_PICKING_UP else order.cus_pos
        if not self.route:
            if self.position == target:
                self._arrive()
                return
            self.route = PathPlanner.build_route(self.position, target)
            self.special_case = PathPlanner.is_straight(self.position, target)

        self.x, self.y = PathPlanner.advance(self.x, self.y, self.route, self.speed)
        if not self.route and self.position == target:
            self._arrive()

    def _arrive(self) -> None:
        """Handle arrival at the current leg's destination."""
        order = self.current_order
        now = self._now()
        if self.state == STATE_PICKING_UP:
            order.mark_picked_up(now)
            self.state = STATE_DELIVERING
            self.route = []
            self._record("arrived_at_merchant", order.id)
            return

        if self.state == STATE_DELIVERING:
            order.complete(now)
            self._record("delivered_to_customer", order.id)
            if order in self.orders:
                self.orders.remove(order)
            self._accepted_ids.discard(order.id)
            self.current_order = None
            self.route = []
            self.state = STATE_IDLE
            self._accept_next_order()

    def recover(self) -> None:
        """Reset transient movement data after an unexpected error."""
        self.route = []
        if self.current_order is None and self.state != STATE_IDLE:
            self.state = STATE_IDLE
        logger.warning("Rider #%d recovered to state %s.", self.rider_id, self.state_name)
