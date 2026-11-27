"""Rider entity: position, state machine, movement and event log.

State machine
-------------
Idle (0) -> Picking Up (1) when an order is assigned (``accepted_order``)
Picking Up (1) -> Delivering (2) on reaching the restaurant
    (``arrived_at_merchant``)
Delivering (2) -> Picking Up (1) if another order is waiting, or
Delivering (2) -> Idle (0) if none remain (``delivered_to_customer``)
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional, Sequence, Tuple

import globalvar
from order_model import COMPLETED, Order
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

DEFAULT_SPEED = 20
DEFAULT_SPAWN = (400, 400)

EVENT_SPAWN = "spawn"
EVENT_ACCEPTED = "accepted_order"
EVENT_ARRIVED = "arrived_at_merchant"
EVENT_DELIVERED = "delivered_to_customer"


def _current_tick() -> int:
    """Return the current simulation tick from the global store."""
    return int(globalvar.get_value("sim_time", 0) or 0)


class Rider:
    """A delivery rider that moves along the street grid.

    Attributes:
        rider_id: Unique identifier.
        x, y: Current coordinates.
        speed: Movement speed in units per tick.
        state: 0 idle, 1 picking up, 2 delivering.
        orders: All orders ever assigned (delivery history included).
        special_case: True while travelling in a straight line that is
            directly above/below (or left/right of) the current target.
        log: Chronological list of event dictionaries. Each entry has the
            keys ``event``, ``order_id``, ``time``, ``x``, ``y`` and ``state``.
        distance_travelled: Total distance moved in map units.
    """

    def __init__(
        self,
        rider_id: int,
        speed: int = DEFAULT_SPEED,
        position: Sequence[int] = DEFAULT_SPAWN,
    ) -> None:
        """Create a rider on a street and log the spawn event.

        Args:
            rider_id: Unique rider identifier.
            speed: Units per tick.
            position: Starting coordinates ``(x, y)``.
        """
        self.rider_id: int = int(rider_id)
        self.x: int = int(position[0])
        self.y: int = int(position[1])
        self.speed: int = int(speed)
        self.state: int = STATE_IDLE
        self.orders: List[Order] = []
        self.special_case: bool = False
        self.log: List[Dict[str, Any]] = []
        self.distance_travelled: int = 0
        self._record(EVENT_SPAWN, None)

    # ------------------------------------------------------------------ #
    # Accessors
    # ------------------------------------------------------------------ #
    @property
    def position(self) -> Tuple[int, int]:
        """Current ``(x, y)`` position."""
        return (self.x, self.y)

    @property
    def state_name(self) -> str:
        """Human-readable name of the current state."""
        return STATE_NAMES.get(self.state, "unknown")

    def active_orders(self) -> List[Order]:
        """Return orders assigned to this rider that are not yet completed."""
        return [order for order in self.orders if order.status != COMPLETED]

    def current_order(self) -> Optional[Order]:
        """Return the order being served now (earliest active), or None."""
        active = self.active_orders()
        return active[0] if active else None

    # ------------------------------------------------------------------ #
    # Simulation
    # ------------------------------------------------------------------ #
    def move(self) -> None:
        """Advance the rider by one tick.

        Handles all state transitions and writes the matching log entries.
        Movement consumes up to ``speed`` units of travel per tick.
        """
        order = self.current_order()
        if order is None:
            self.state = STATE_IDLE
            self.special_case = False
            return

        if self.state == STATE_IDLE:
            self._start_pickup(order)

        if self.state == STATE_PICKING_UP:
            if self._travel(order.res_pos):
                self.state = STATE_DELIVERING
                order.mark_picked_up(_current_tick())
                self._record(EVENT_ARRIVED, order.id)
        elif self.state == STATE_DELIVERING:
            if self._travel(order.cus_pos):
                self._complete_delivery(order)

    def _travel(self, target: Tuple[int, int]) -> bool:
        """Move toward ``target`` along the streets using this tick's budget.

        Args:
            target: Destination grid corner.

        Returns:
            True if the rider is at the target after moving.
        """
        tx, ty = target
        budget = self.speed
        while budget > 0 and (self.x, self.y) != (tx, ty):
            nx, ny, used = PathPlanner.next_position(self.x, self.y, tx, ty, budget)
            if used == 0:
                break
            self.x, self.y = nx, ny
            budget -= used
            self.distance_travelled += used
        at_target = (self.x, self.y) == (tx, ty)
        self.special_case = (not at_target) and (self.x == tx or self.y == ty)
        return at_target

    def _start_pickup(self, order: Order) -> None:
        """Enter the picking-up state for ``order`` and log acceptance."""
        self.state = STATE_PICKING_UP
        order.mark_accepted(_current_tick())
        self._record(EVENT_ACCEPTED, order.id)

    def _complete_delivery(self, order: Order) -> None:
        """Finish ``order``, then either start the next order or go idle."""
        order.complete(_current_tick())
        self._record(EVENT_DELIVERED, order.id)
        next_order = self.current_order()
        if next_order is not None:
            self._start_pickup(next_order)
        else:
            self.state = STATE_IDLE
            self.special_case = False

    def _record(self, event: str, order_id: Optional[int]) -> None:
        """Append a status-change entry to the rider log."""
        self.log.append(
            {
                "event": event,
                "order_id": order_id,
                "rider_id": self.rider_id,
                "time": _current_tick(),
                "x": self.x,
                "y": self.y,
                "state": self.state,
            }
        )

    def to_dict(self) -> Dict[str, Any]:
        """Return a JSON-serialisable representation of the rider."""
        return {
            "rider_id": self.rider_id,
            "x": self.x,
            "y": self.y,
            "speed": self.speed,
            "state": self.state,
            "special_case": self.special_case,
            "distance_travelled": self.distance_travelled,
            "order_ids": [order.id for order in self.orders],
            "log": list(self.log),
        }

    def __repr__(self) -> str:
        return (
            f"Rider(id={self.rider_id}, pos=({self.x},{self.y}), "
            f"state={self.state_name}, orders={len(self.orders)})"
        )
