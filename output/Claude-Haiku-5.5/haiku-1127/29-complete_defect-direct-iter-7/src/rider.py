"""Rider entity: state machine, street-grid movement and status log.

State transitions
    IDLE (0) -> PICKING_UP (1)   when the rider accepts its next order
    PICKING_UP (1) -> DELIVERING (2)   on arrival at the restaurant
    DELIVERING (2) -> IDLE (0)   on delivery to the customer

Transitions and their log entries are produced inside :meth:`Rider.move`.
"""

from __future__ import annotations

import logging
from typing import Any

import config
import globalvar
from order_model import (
    STATUS_ASSIGNED,
    STATUS_DELIVERING,
    STATUS_PICKING_UP,
)
from path_planner import PathPlanner

logger = logging.getLogger("dispatch.rider")

STATE_IDLE = 0
STATE_PICKING_UP = 1
STATE_DELIVERING = 2
STATE_NAMES = {
    STATE_IDLE: "idle",
    STATE_PICKING_UP: "picking up",
    STATE_DELIVERING: "delivering",
}


def current_tick() -> int:
    """Return the current simulated tick from the global store."""
    return int(globalvar.get_value("tick", 0))


class Rider:
    """A delivery rider that moves along the street grid.

    Attributes:
        rider_id: Unique identifier.
        x, y: Current position in map units (0-800).
        speed: Movement speed in units per tick.
        state: 0 idle, 1 picking up, 2 delivering.
        orders: Assigned orders; ``orders[0]`` is the active order.
        special_case: True while on a straight leg or yielding to a rider.
        waypoints: Remaining waypoints of the current leg.
        log: Status-change records (dicts with "event", "order_id", ...).
    """

    def __init__(self, rider_id: int, x: int | None = None,
                 y: int | None = None, speed: int | None = None) -> None:
        """Create a rider and record its spawn event.

        Args:
            rider_id: Unique positive identifier.
            x: Initial x coordinate (defaults to the centre of cell (0, 0)).
            y: Initial y coordinate (defaults to the centre of cell (0, 0)).
            speed: Movement speed in units per tick (defaults to
                config.DEFAULT_SPEED).

        Raises:
            ValueError: If any argument is invalid.
        """
        if isinstance(rider_id, bool) or not isinstance(rider_id, int) \
                or rider_id <= 0:
            raise ValueError("rider_id must be a positive integer")
        half = config.CELL_SIZE // 2
        x = half if x is None else x
        y = half if y is None else y
        speed = config.DEFAULT_SPEED if speed is None else speed
        if isinstance(speed, bool) or not isinstance(speed, int) or speed <= 0:
            raise ValueError("speed must be a positive integer")
        for value in (x, y):
            if isinstance(value, bool) or not isinstance(value, int) \
                    or not 0 <= value <= config.MAP_SIZE:
                raise ValueError(
                    f"rider position must be integers in 0-{config.MAP_SIZE}")

        self.rider_id = rider_id
        self.x = x
        self.y = y
        self.speed = speed
        self.state = STATE_IDLE
        self.orders: list[Any] = []
        self.special_case = False
        self.waypoints: list[tuple[int, int]] = []
        self.log: list[dict] = []
        self._tick_events: list[dict] = []
        self._wait_ticks = 0
        self._prefer_vertical = False
        self._record("spawn", None)

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------
    @property
    def position(self) -> tuple[int, int]:
        """Current (x, y) position."""
        return self.x, self.y

    def _record(self, event: str, order_id: int | None) -> dict:
        """Append a status-change record to the rider log.

        Args:
            event: Event name (spawn, accepted_order, arrived_at_merchant,
                delivered_to_customer, recovered).
            order_id: Related order identifier, or None.

        Returns:
            dict: The recorded entry.
        """
        entry = {
            "event": event,
            "order_id": order_id,
            "rider_id": self.rider_id,
            "tick": current_tick(),
            "x": self.x,
            "y": self.y,
            "state": self.state,
        }
        self.log.append(entry)
        if len(self.log) > config.LOG_LIMIT:
            del self.log[: len(self.log) - config.LOG_LIMIT]
        self._tick_events.append(dict(entry))
        logger.info("Rider %d: %s (order %s) at (%d,%d)",
                    self.rider_id, event, order_id, self.x, self.y)
        return entry

    def _blocked_at(self, pos: tuple[int, int]) -> bool:
        """Return True if another moving rider occupies ``pos``."""
        for other in globalvar.get_value("riders", []) or []:
            if other is self or other.state == STATE_IDLE:
                continue
            if other.position == pos:
                return True
        return False

    def _replan_alternate(self) -> None:
        """Switch the current leg to the alternate street route."""
        if not self.waypoints:
            return
        destination = self.waypoints[-1]
        self._prefer_vertical = not self._prefer_vertical
        self.waypoints = PathPlanner.plan(
            self.position, destination, prefer_vertical=self._prefer_vertical)
        logger.debug("Rider %d replanned route to %s", self.rider_id,
                     destination)

    def _accept_next_order(self) -> bool:
        """Accept the next assigned order if one is waiting.

        Returns:
            bool: True if the rider transitioned to PICKING_UP.
        """
        if not self.orders:
            return False
        order = self.orders[0]
        if order.status != STATUS_ASSIGNED:
            return False
        self.state = STATE_PICKING_UP
        order.mark_status(STATUS_PICKING_UP)
        order.accept_tick = current_tick()
        self._wait_ticks = 0
        self._prefer_vertical = False
        self.waypoints = PathPlanner.plan(self.position, order.res_pos)
        self.special_case = len(self.waypoints) == 1
        self._record("accepted_order", order.id)
        return True

    def _travel(self) -> None:
        """Move up to ``speed`` units along the current route.

        If the destination cell is occupied by another moving rider, the
        rider waits.  After WAIT_REPLAN_TICKS it switches to the alternate
        route; after WAIT_GIVEUP_TICKS it proceeds anyway to avoid deadlock.
        """
        new_pos, remaining = PathPlanner.advance(
            self.position, self.waypoints, self.speed)
        if new_pos != self.position and self._blocked_at(new_pos):
            self._wait_ticks += 1
            self.special_case = True
            if self._wait_ticks < config.WAIT_GIVEUP_TICKS:
                if self._wait_ticks == config.WAIT_REPLAN_TICKS:
                    self._replan_alternate()
                return
            logger.warning("Rider %d proceeding after %d blocked ticks",
                           self.rider_id, self._wait_ticks)
        self._wait_ticks = 0
        self.x, self.y = new_pos
        self.waypoints = remaining
        self.special_case = len(remaining) == 1

    def _resolve_arrivals(self) -> None:
        """Process pickup and delivery arrivals and state transitions."""
        while not self.waypoints and self.state != STATE_IDLE:
            if not self.orders:
                logger.error("Rider %d was busy without orders; going idle",
                             self.rider_id)
                self.state = STATE_IDLE
                break
            order = self.orders[0]
            if self.state == STATE_PICKING_UP:
                self.state = STATE_DELIVERING
                order.mark_status(STATUS_DELIVERING)
                order.pickup_tick = current_tick()
                self._wait_ticks = 0
                self._prefer_vertical = False
                self.waypoints = PathPlanner.plan(self.position, order.cus_pos)
                self.special_case = len(self.waypoints) == 1
                self._record("arrived_at_merchant", order.id)
            else:
                self.orders.pop(0)
                order.complete(current_tick())
                self.state = STATE_IDLE
                self.special_case = False
                self._wait_ticks = 0
                self._record("delivered_to_customer", order.id)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------
    def move(self) -> list[dict]:
        """Advance the rider by one simulated tick.

        Performs the idle-to-picking-up transition when an order is waiting,
        moves along the current route, and performs arrival transitions.

        Returns:
            list[dict]: Status-change records produced during this tick.
        """
        self._tick_events = []
        if self.state == STATE_IDLE and not self._accept_next_order():
            return []
        if self.waypoints:
            self._travel()
        self._resolve_arrivals()
        return list(self._tick_events)

    def recover(self) -> None:
        """Restore a consistent state after an unexpected error.

        A rider still heading to the restaurant gives its order back to the
        queue (status ASSIGNED).  A rider already delivering re-plans its
        route to the customer.
        """
        order_id = None
        if self.orders:
            order_id = self.orders[0].id
        if self.state == STATE_PICKING_UP and self.orders:
            self.orders[0].mark_status(STATUS_ASSIGNED)
            self.state = STATE_IDLE
            self.waypoints = []
        elif self.state == STATE_DELIVERING and self.orders:
            self.waypoints = PathPlanner.plan(self.position,
                                              self.orders[0].cus_pos)
        else:
            self.state = STATE_IDLE
            self.waypoints = []
        self.special_case = False
        self._wait_ticks = 0
        self._record("recovered", order_id)

    def to_dict(self) -> dict:
        """Serialise the rider to a JSON-compatible dictionary.

        Returns:
            dict: Rider attributes (the log is excluded).
        """
        return {
            "rider_id": self.rider_id,
            "x": self.x,
            "y": self.y,
            "speed": self.speed,
            "state": self.state,
            "state_name": STATE_NAMES.get(self.state, "unknown"),
            "orders": [order.id for order in self.orders],
            "special_case": self.special_case,
        }
