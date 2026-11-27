"""Rider model: state machine, movement and event log.

Rider states:
    0 = idle, 1 = picking up (en route to restaurant),
    2 = delivering (en route to customer).

Events written to ``Rider.log``:
    "spawn", "accepted_order", "arrived_at_merchant",
    "delivered_to_customer".
"""

import logging
from typing import Any, Dict, List, Optional, Tuple

import globalvar
from path_planner import PathPlanner, is_on_street

logger = logging.getLogger(__name__)

IDLE = 0
PICKING_UP = 1
DELIVERING = 2

STATE_NAMES = {IDLE: "idle", PICKING_UP: "picking up", DELIVERING: "delivering"}

DEFAULT_SPEED = 10
SPAWN_X = 435
SPAWN_Y = 385
MAX_WAIT_TICKS = 3

Point = Tuple[int, int]


class Rider:
    """A delivery rider that follows street routes one tick at a time.

    Attributes:
        rider_id: Unique identifier.
        x, y: Current coordinates.
        speed: Movement budget in units per tick.
        state: Integer status (0 idle, 1 picking up, 2 delivering).
        orders: Assigned orders; index 0 is the active order.
        special_case: True while the rider is waiting for another rider.
        log: Chronological list of event dictionaries.
        path: Remaining waypoints of the current leg.
    """

    def __init__(self, rider_id: int, speed: int = DEFAULT_SPEED) -> None:
        """Create a rider at the spawn location in the idle state.

        Args:
            rider_id: Unique identifier for the rider.
            speed: Movement speed in units per tick.
        """
        self.rider_id: int = int(rider_id)
        self.x: int = SPAWN_X
        self.y: int = SPAWN_Y
        self.speed: int = int(speed)
        self.state: int = IDLE
        self.orders: List[Any] = []
        self.special_case: bool = False
        self.log: List[Dict[str, Any]] = []
        self.path: List[Point] = []
        self._wait_ticks: int = 0
        self._planner = PathPlanner()
        self._record("spawn", None)

    # ------------------------------------------------------------------
    # Properties and helpers
    # ------------------------------------------------------------------
    @property
    def position(self) -> Point:
        """Return the current ``(x, y)`` position."""
        return (self.x, self.y)

    @property
    def state_name(self) -> str:
        """Return a human-readable name for the current state."""
        return STATE_NAMES.get(self.state, "unknown")

    def current_order(self) -> Optional[Any]:
        """Return the active order, or None if the rider has none."""
        return self.orders[0] if self.orders else None

    def _now(self) -> int:
        """Return the current simulated tick."""
        return int(globalvar.get_value("time", 0) or 0)

    def _record(self, event: str, order_id: Optional[int]) -> None:
        """Append an event entry to the rider log."""
        self.log.append({
            "event": event,
            "order_id": order_id,
            "time": self._now(),
            "x": self.x,
            "y": self.y,
            "state": self.state,
            "rider_id": self.rider_id,
        })

    def to_dict(self) -> Dict[str, Any]:
        """Return a JSON-serialisable representation of the rider."""
        return {
            "rider_id": self.rider_id,
            "x": self.x,
            "y": self.y,
            "speed": self.speed,
            "state": self.state,
            "special_case": self.special_case,
            "order_ids": [o.id for o in self.orders],
            "log": list(self.log),
        }

    # ------------------------------------------------------------------
    # Simulation
    # ------------------------------------------------------------------
    def move(self) -> None:
        """Advance the rider by one tick.

        Handles the state transitions:
            idle -> picking up when an order is present,
            picking up -> delivering on arrival at the restaurant,
            delivering -> idle on arrival at the customer.
        """
        if self.state == IDLE:
            if not self.orders:
                return
            self._start_pickup()

        budget = self.speed
        while True:
            budget = self._advance(budget)
            if self.path:
                return
            if self.state == PICKING_UP:
                self._arrive_merchant()
            elif self.state == DELIVERING:
                self._deliver()
                return
            else:
                return

    def _start_pickup(self) -> None:
        """Begin the pickup leg for the active order."""
        order = self.orders[0]
        self.state = PICKING_UP
        order.status = "picking_up"
        self.path = self._planner.plan((self.x, self.y), order.res_pos)[1:]
        self._record("accepted_order", order.id)

    def _arrive_merchant(self) -> None:
        """Handle arrival at the restaurant and plan the delivery leg."""
        order = self.orders[0]
        self._record("arrived_at_merchant", order.id)
        self.state = DELIVERING
        order.status = "delivering"
        self.path = self._planner.plan((self.x, self.y), order.cus_pos)[1:]

    def _deliver(self) -> None:
        """Handle delivery completion and release the rider."""
        order = self.orders.pop(0)
        order.mark_completed(self._now())
        self._record("delivered_to_customer", order.id)
        completed = globalvar.get_value("completed_orders")
        if completed is not None:
            completed.append(order)
        self.state = IDLE
        self.path = []
        self._wait_ticks = 0
        self.special_case = False

    def _advance(self, budget: int) -> int:
        """Consume movement budget along the current path.

        Returns:
            The unused budget. The rider stops early when it must wait for a
            blocking rider; the wait is limited to MAX_WAIT_TICKS to avoid
            deadlock.
        """
        while budget > 0 and self.path:
            nxt = self.path[0]
            if self._is_blocked(nxt):
                if self._wait_ticks < MAX_WAIT_TICKS:
                    self._wait_ticks += 1
                    self.special_case = True
                    return 0
                logger.info("Rider %s breaks deadlock at %s",
                            self.rider_id, nxt)
                self._wait_ticks = 0
            self.special_case = False
            budget -= self._step_towards(nxt, budget)
            if (self.x, self.y) == nxt:
                self.path.pop(0)
        return budget

    def _step_towards(self, target: Point, budget: int) -> int:
        """Move along an axis-aligned segment towards ``target``.

        Returns:
            The distance actually moved.
        """
        dx = target[0] - self.x
        dy = target[1] - self.y
        dist = abs(dx) + abs(dy)
        if dist <= budget:
            self.x, self.y = target
            return dist
        if dx != 0:
            step = min(budget, abs(dx))
            self.x += step if dx > 0 else -step
            return step
        step = min(budget, abs(dy))
        self.y += step if dy > 0 else -step
        return step

    def _is_blocked(self, point: Point) -> bool:
        """Return True if another busy rider occupies ``point``."""
        for other in globalvar.get_value("riders") or []:
            if other is self:
                continue
            if other.state != IDLE and other.position == point:
                return True
        return False

    def __repr__(self) -> str:
        return (f"Rider(id={self.rider_id}, pos=({self.x},{self.y}), "
                f"state={self.state_name}, orders={len(self.orders)}, "
                f"on_street={is_on_street((self.x, self.y))})")
