"""Rider model: state, movement and delivery workflow.

A rider cycles through three states:

* 0 (idle): no orders are assigned.
* 1 (picking up): travelling to the restaurant of the first order.
* 2 (delivering): travelling to the customer of the first order.

State transitions and their log entries happen inside ``Rider.move``.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional, Set, Tuple

from config import get_config
from globalvar import get_value
from path_planner import GridMap, PathPlanner

logger = logging.getLogger(__name__)

STATE_IDLE = 0
STATE_PICKING_UP = 1
STATE_DELIVERING = 2

STATE_NAMES = {
    STATE_IDLE: "idle",
    STATE_PICKING_UP: "picking_up",
    STATE_DELIVERING: "delivering",
}

EVENT_SPAWN = "spawn"
EVENT_ACCEPTED = "accepted_order"
EVENT_ARRIVED_MERCHANT = "arrived_at_merchant"
EVENT_DELIVERED = "delivered_to_customer"


class Rider:
    """A delivery rider that moves on the grid and serves orders.

    Attributes:
        rider_id: Unique identifier of the rider.
        x: Current x coordinate in units.
        y: Current y coordinate in units.
        speed: Movement speed in units per tick.
        state: Current status (0 idle, 1 picking up, 2 delivering).
        orders: Assigned orders, served in order; the first one is active.
        special_case: True when the current leg is a straight line directly
            above, below, or beside the target.
        log: Status-change events with keys "event", "order_id", "time", etc.
        path: Remaining waypoints of the current route.
    """

    def __init__(self, rider_id: int) -> None:
        """Create a rider at the depot (centre of cell 0,0) in the idle state.

        Args:
            rider_id: Unique identifier for the rider.
        """
        cfg = get_config()
        grid = GridMap.from_config()
        self.rider_id = int(rider_id)
        self.x, self.y = grid.snap(0, 0)
        self.speed = int(cfg.default_speed)
        self.state = STATE_IDLE
        self.orders: List[Any] = []
        self.special_case = False
        self.log: List[Dict[str, Any]] = []
        self.path: List[Tuple[int, int]] = []
        self.planner = PathPlanner(grid)
        self._log(EVENT_SPAWN, None)
        logger.info("Rider #%d spawned at (%d, %d)", self.rider_id, self.x, self.y)

    @property
    def position(self) -> Tuple[int, int]:
        """Return the current (x, y) position."""
        return self.x, self.y

    def move(self) -> None:
        """Advance the rider by one tick.

        The rider accepts new work when idle, spends up to ``speed`` units
        along its route, and performs state transitions when it reaches a
        destination: arriving at the restaurant starts the delivery leg, and
        arriving at the customer completes the order.
        """
        if self.state == STATE_IDLE:
            if not self.orders:
                return
            self._begin_pickup()

        budget = int(self.speed)
        while self.orders:
            if not self.path:
                if not self._on_leg_complete():
                    break
                continue
            if budget <= 0:
                break
            target = self.path[0]
            budget = self._step_toward(target, budget)
            if (self.x, self.y) == target:
                self.path.pop(0)

    def resync(self) -> Optional[str]:
        """Repair an inconsistent state after an unexpected failure.

        Returns:
            A description of the repaired inconsistency, or None if healthy.
        """
        if self.state == STATE_IDLE and self.orders:
            self._begin_pickup()
            return f"rider #{self.rider_id} had orders while idle; pickup restarted"
        if self.state != STATE_IDLE and not self.orders:
            self.state = STATE_IDLE
            self.path = []
            self.special_case = False
            return f"rider #{self.rider_id} was busy without orders; reset to idle"
        return None

    def to_dict(self) -> Dict[str, Any]:
        """Return a JSON-serialisable representation of the rider.

        Returns:
            Dictionary with the rider attributes and status log.
        """
        return {
            "rider_id": self.rider_id,
            "x": self.x,
            "y": self.y,
            "speed": self.speed,
            "state": self.state,
            "orders": [order.id for order in self.orders],
            "special_case": self.special_case,
            "log": list(self.log),
        }

    def _begin_pickup(self) -> None:
        """Switch to the picking-up state for the first assigned order."""
        self.state = STATE_PICKING_UP
        order = self.orders[0]
        self._log(EVENT_ACCEPTED, order.id)
        self._set_path(order.restaurant_pos)

    def _on_leg_complete(self) -> bool:
        """Handle arrival at the current destination.

        Returns:
            True if a new leg was started and movement should continue,
            False if the rider has no further work this tick.
        """
        if not self.orders:
            return False
        order = self.orders[0]

        if self.state == STATE_PICKING_UP:
            self._log(EVENT_ARRIVED_MERCHANT, order.id)
            self.state = STATE_DELIVERING
            self._set_path(order.customer_pos)
            return True

        if self.state == STATE_DELIVERING:
            self.orders.pop(0)
            order.complete(_current_tick())
            completed = get_value("completed_orders")
            if completed is not None:
                completed.append(order)
            self._log(EVENT_DELIVERED, order.id)
            if self.orders:
                self._begin_pickup()
                return True
            self.state = STATE_IDLE
            self.path = []
            self.special_case = False
            return False

        return False

    def _set_path(self, target: Tuple[int, int]) -> None:
        """Plan a route from the current position to ``target``.

        Args:
            target: Destination cell centre.
        """
        occupied = {
            (rider.x, rider.y)
            for rider in (get_value("riders") or [])
            if rider is not self
        }  # type: Set[Tuple[int, int]]
        self.path = self.planner.plan((self.x, self.y), target, occupied)
        self.special_case = self.x == target[0] or self.y == target[1]

    def _step_toward(self, target: Tuple[int, int], budget: int) -> int:
        """Move along one axis-aligned direction toward ``target``.

        Args:
            target: Waypoint to approach.
            budget: Remaining movement units for this tick.

        Returns:
            The movement budget left after this step.
        """
        tx, ty = target
        dx = tx - self.x
        if dx and budget > 0:
            step = min(abs(dx), budget)
            self.x += step if dx > 0 else -step
            budget -= step
        dy = ty - self.y
        if dy and budget > 0:
            step = min(abs(dy), budget)
            self.y += step if dy > 0 else -step
            budget -= step
        return budget

    def _log(self, event: str, order_id: Optional[int]) -> None:
        """Append a status-change entry to the rider log.

        Args:
            event: Event name, e.g. "accepted_order".
            order_id: Related order identifier, or None.
        """
        entry = {
            "event": event,
            "order_id": order_id,
            "time": _current_tick(),
            "rider_id": self.rider_id,
            "x": self.x,
            "y": self.y,
            "state": self.state,
        }
        self.log.append(entry)
        logger.debug("Rider #%d %s order=%s at (%d, %d)",
                     self.rider_id, event, order_id, self.x, self.y)

    def __repr__(self) -> str:
        """Return a short textual description of the rider."""
        return (f"Rider(id={self.rider_id}, pos=({self.x}, {self.y}), "
                f"state={STATE_NAMES.get(self.state, self.state)}, "
                f"orders={[o.id for o in self.orders]})")


def _current_tick() -> int:
    """Return the simulated clock value from the global store."""
    return int(get_value("current_tick", 0) or 0)
