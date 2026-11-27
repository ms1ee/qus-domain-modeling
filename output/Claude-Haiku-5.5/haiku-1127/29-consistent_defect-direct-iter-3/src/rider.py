"""Rider model: state machine, street-based movement and event logging."""

import logging
from typing import Any, Dict, List, Optional, Tuple

import globalvar
from config import RIDER_SPEED, RIDER_START_X, RIDER_START_Y
from path_planner import PathPlanner

logger = logging.getLogger("dispatch.rider")

# Rider state enumeration.
IDLE = 0
PICKING_UP = 1
DELIVERING = 2

STATE_NAMES = {IDLE: "idle", PICKING_UP: "picking up", DELIVERING: "delivering"}

# Order statuses that have not been accepted by a rider yet.
_NOT_STARTED = ("created", "assigned")


def _configured_speed() -> int:
    """Return the rider speed from the active configuration."""
    cfg = globalvar.get_value("config") or {}
    try:
        return int(cfg.get("rider_speed", RIDER_SPEED))
    except (TypeError, ValueError):
        return RIDER_SPEED


class Rider:
    """A delivery rider that moves on the street grid and serves orders.

    Orders are assigned by appending them to ``rider.orders``. Orders are
    served in assignment order. Completed orders remain in ``orders`` as
    delivery history.

    Attributes:
        rider_id: Unique integer identifier.
        x: Current x coordinate (0-800).
        y: Current y coordinate (0-800).
        speed: Movement speed in units per tick.
        state: 0 idle, 1 picking up, 2 delivering.
        orders: All orders ever assigned to this rider.
        special_case: True while moving in a straight line toward the target
            (directly above/below or left/right of it).
        log: Chronological list of event dictionaries. Each contains the keys
            ``"event"`` and ``"order_id"`` plus ``"time"``, ``"rider_id"``,
            ``"x"``, ``"y"`` and ``"state"``.
    """

    def __init__(self, rider_id: int) -> None:
        """Create a rider at the default start position (400, 400).

        Args:
            rider_id: Unique identifier assigned by the system.
        """
        self.rider_id: int = int(rider_id)
        self.x: int = RIDER_START_X
        self.y: int = RIDER_START_Y
        self.speed: int = _configured_speed()
        self.state: int = IDLE
        self.orders: List[Any] = []
        self.special_case: bool = False
        self.log: List[Dict[str, Any]] = []
        self._record("spawn", None)

    @property
    def position(self) -> Tuple[int, int]:
        """Return the current ``(x, y)`` position."""
        return self.x, self.y

    def active_orders(self) -> List[Any]:
        """Return orders that are not yet completed, in service order."""
        return [order for order in self.orders if order.status != "completed"]

    def current_order(self) -> Optional[Any]:
        """Return the order currently being served, or None if idle."""
        active = self.active_orders()
        return active[0] if active else None

    def is_idle(self) -> bool:
        """Return True if the rider has no active orders."""
        return not self.active_orders()

    def move(self) -> None:
        """Advance the rider by one tick.

        Handles state transitions:
          * Idle -> Picking up when a new order is accepted.
          * Picking up -> Delivering on arrival at the restaurant.
          * Delivering -> Picking up (next order) or Idle on delivery.
        """
        current = self.current_order()
        if current is None:
            if self.state != IDLE or self.special_case:
                self.state = IDLE
                self.special_case = False
            return

        if current.status in _NOT_STARTED:
            current.status = "picking_up"
            self.state = PICKING_UP
            self._record("accepted_order", current.id)

        if current.status == "delivering":
            self.state = DELIVERING
        else:
            self.state = PICKING_UP

        if self.state == PICKING_UP:
            if self._advance(current.res_pos):
                current.status = "delivering"
                self.state = DELIVERING
                self._record("arrived_at_merchant", current.id)
        else:
            if self._advance(current.cus_pos):
                current.complete(globalvar.get_value("time", 0))
                self._record("delivered_to_customer", current.id)
                self.state = PICKING_UP if self.current_order() is not None else IDLE
                self.special_case = False

    def _advance(self, target: Tuple[int, int]) -> bool:
        """Move up to ``speed`` units toward ``target`` along streets.

        Args:
            target: Destination grid point.

        Returns:
            True if the rider is located at the target after moving.
        """
        tx, ty = target
        self.x, self.y = PathPlanner.next_position(self.x, self.y, tx, ty, self.speed)
        self.special_case = (self.x == tx) != (self.y == ty)
        return (self.x, self.y) == (tx, ty)

    def _record(self, event: str, order_id: Optional[int]) -> None:
        """Append an entry to the rider's event log.

        Args:
            event: Event name (spawn, accepted_order, arrived_at_merchant,
                delivered_to_customer).
            order_id: Related order identifier, or None.
        """
        entry = {
            "event": event,
            "order_id": order_id,
            "time": globalvar.get_value("time", 0),
            "rider_id": self.rider_id,
            "x": self.x,
            "y": self.y,
            "state": self.state,
        }
        self.log.append(entry)
        logger.debug("Rider %s: %s (order %s)", self.rider_id, event, order_id)

    def __repr__(self) -> str:
        return (f"Rider(id={self.rider_id}, pos=({self.x}, {self.y}), "
                f"state={STATE_NAMES[self.state]}, active={len(self.active_orders())})")
