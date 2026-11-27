"""Rider model: movement, state machine and order execution.

State machine:
    IDLE (0) -> PICKING_UP (1) when an order is assigned and accepted,
    PICKING_UP (1) -> DELIVERING (2) on arrival at the restaurant,
    DELIVERING (2) -> IDLE (0) on arrival at the customer.

State transitions and their log entries happen inside ``Rider.move``.
Riders never block each other, so no deadlock can occur between them.
"""

from typing import Any, Dict, List, Optional

import globalvar
from config import LOGGER, RIDER_SPEED, RIDER_START_X, RIDER_START_Y
from path_planner import PathPlanner, Point

IDLE = 0
PICKING_UP = 1
DELIVERING = 2

STATE_NAMES = {
    IDLE: "idle",
    PICKING_UP: "picking up",
    DELIVERING: "delivering",
}

EVENT_SPAWN = "spawn"
EVENT_ACCEPTED = "accepted_order"
EVENT_ARRIVED_MERCHANT = "arrived_at_merchant"
EVENT_DELIVERED = "delivered_to_customer"

_planner = PathPlanner()


def _current_tick() -> int:
    """Return the simulation tick stored in the global variable store."""
    value = globalvar.get_value("current_tick")
    return int(value) if value is not None else 0


class Rider:
    """A delivery rider that moves on the street grid and executes orders.

    Attributes:
        rider_id: Unique identifier.
        x: Current x coordinate.
        y: Current y coordinate.
        speed: Movement speed in units per tick.
        state: Integer state (0 idle, 1 picking up, 2 delivering).
        orders: Assigned orders; the first element is the active order.
        special_case: True while the rider is off the street network.
        path: Remaining axis-aligned waypoints of the current leg.
        log: Chronological list of event dictionaries.
    """

    def __init__(self, rider_id: int) -> None:
        """Create an idle rider at the default start location.

        Args:
            rider_id: Unique identifier assigned by the system.
        """
        start = globalvar.get_value("rider_start") or (RIDER_START_X, RIDER_START_Y)
        speed = globalvar.get_value("rider_speed")
        self.rider_id = int(rider_id)
        self.x = int(start[0])
        self.y = int(start[1])
        self.speed = int(speed) if speed else RIDER_SPEED
        self.state = IDLE
        self.orders: List[Any] = []
        self.path: List[Point] = []
        self.special_case = not _planner.is_on_street(self.position)
        self.log: List[Dict[str, Any]] = []
        self._record(EVENT_SPAWN, None)

    @property
    def position(self) -> Point:
        """Return the current ``(x, y)`` position."""
        return (self.x, self.y)

    @property
    def state_name(self) -> str:
        """Return a human-readable name for the current state."""
        return STATE_NAMES.get(self.state, "unknown")

    @property
    def current_order(self) -> Optional[Any]:
        """Return the active order or ``None`` if there is none."""
        return self.orders[0] if self.orders else None

    def _record(self, event: str, order_id: Optional[int]) -> None:
        """Append a log entry describing the rider at the current tick."""
        self.log.append(
            {
                "event": event,
                "order_id": order_id,
                "tick": _current_tick(),
                "rider_id": self.rider_id,
                "x": self.x,
                "y": self.y,
                "state": self.state,
            }
        )
        LOGGER.info(
            "rider %d %s order=%s at (%d,%d)",
            self.rider_id,
            event,
            order_id,
            self.x,
            self.y,
        )

    def _start_pickup(self) -> None:
        """Accept the first assigned order and plan the route to the restaurant."""
        order = self.orders[0]
        self.state = PICKING_UP
        order.set_status("picking_up")
        self.path = _planner.plan(self.position, order.res_pos)
        self._record(EVENT_ACCEPTED, order.id)

    def _on_arrival(self) -> None:
        """Handle reaching the current leg's destination.

        Arriving at the restaurant starts the delivery leg; arriving at the
        customer completes the order and frees the rider.
        """
        if not self.orders:
            self.state = IDLE
            self.path = []
            return
        order = self.orders[0]
        if self.state == PICKING_UP:
            self.state = DELIVERING
            order.set_status("delivering")
            self.path = _planner.plan(self.position, order.cus_pos)
            self._record(EVENT_ARRIVED_MERCHANT, order.id)
        elif self.state == DELIVERING:
            order.mark_completed(_current_tick())
            self._record(EVENT_DELIVERED, order.id)
            self.orders.pop(0)
            self.state = IDLE
            self.path = []

    def move(self) -> int:
        """Advance the rider by one tick.

        The rider accepts a new order if idle, then spends up to ``speed``
        units along its route. Arrivals trigger state transitions and their
        log entries.

        Returns:
            Number of units moved during this tick.
        """
        if self.state == IDLE:
            if not self.orders:
                return 0
            self._start_pickup()

        remaining = self.speed
        moved_total = 0
        while remaining > 0 and self.state != IDLE:
            if not self.path:
                self._on_arrival()
                continue
            next_point = self.path[0]
            dx = next_point[0] - self.x
            dy = next_point[1] - self.y
            distance = abs(dx) + abs(dy)
            if distance <= remaining:
                self.x, self.y = next_point
                self.path.pop(0)
                remaining -= distance
                moved_total += distance
            else:
                step = remaining
                move_x = min(abs(dx), step)
                self.x += move_x if dx > 0 else -move_x
                step -= move_x
                move_y = min(abs(dy), step)
                self.y += move_y if dy > 0 else -move_y
                step -= move_y
                moved_total += remaining - step
                remaining = step

        if moved_total and self.orders:
            self.orders[0].add_distance(moved_total)
        self.special_case = self.state != IDLE and not _planner.is_on_street(self.position)
        return moved_total

    def to_dict(self) -> Dict[str, Any]:
        """Return a JSON-serialisable snapshot of the rider."""
        return {
            "rider_id": self.rider_id,
            "x": self.x,
            "y": self.y,
            "speed": self.speed,
            "state": self.state,
            "special_case": self.special_case,
            "order_ids": [order.id for order in self.orders],
            "log": list(self.log),
        }
