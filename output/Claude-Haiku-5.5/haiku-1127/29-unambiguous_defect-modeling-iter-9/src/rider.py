"""Rider entity: state machine, street-based movement, and event logging.

Rider state transitions:
    IDLE (0) -> PICKING_UP (1) when an assigned order is accepted
    PICKING_UP (1) -> DELIVERING (2) on arrival at the restaurant
    DELIVERING (2) -> IDLE (0) on delivery to the customer
"""

import logging
from typing import Any, Dict, List, Optional, Tuple

import globalvar
from config import LATTICE_STEP, MAX_LOG_ENTRIES, get_config
from pathplanner import PathPlanner

logger = logging.getLogger(__name__)

IDLE = 0
PICKING_UP = 1
DELIVERING = 2
STATE_NAMES = {IDLE: "Idle", PICKING_UP: "Picking Up", DELIVERING: "Delivering"}

# Deterministic start positions on streets (intersections).
START_POSITIONS: List[Tuple[int, int]] = [
    (100, 100), (500, 100), (100, 500), (500, 500), (300, 300),
    (700, 700), (100, 700), (700, 100), (300, 500), (500, 300),
]


class Rider:
    """A delivery rider who moves along streets and serves queued orders.

    Attributes:
        rider_id: Unique positive identifier.
        x: Current x coordinate (0-800).
        y: Current y coordinate (0-800).
        speed: Movement speed in units per tick.
        state: 0 idle, 1 picking up, 2 delivering.
        orders: Assigned orders; the first element is the active order.
        special_case: True while the rider stands on a restaurant/customer cell.
        path: Remaining waypoints of the current route.
        log: Chronological list of event dictionaries.
    """

    def __init__(self, rider_id: int) -> None:
        """Create a rider on a street with the default speed.

        Args:
            rider_id: Unique positive integer identifier.

        Raises:
            ValueError: If ``rider_id`` is not a positive integer.
        """
        if isinstance(rider_id, bool) or not isinstance(rider_id, int) or rider_id <= 0:
            raise ValueError("rider_id must be a positive integer")
        self.rider_id: int = rider_id
        self.x, self.y = START_POSITIONS[(rider_id - 1) % len(START_POSITIONS)]
        self.speed: int = get_config().default_rider_speed
        self.state: int = IDLE
        self.orders: List[Any] = []
        self.special_case: bool = False
        self.path: List[Tuple[int, int]] = []
        self.log: List[Dict[str, Any]] = []
        self._record("spawn", None)

    # ------------------------------------------------------------------ #
    # Properties and helpers
    # ------------------------------------------------------------------ #
    @property
    def state_name(self) -> str:
        """Human-readable name of the current state."""
        return STATE_NAMES.get(self.state, "Unknown")

    def snapped_position(self) -> Tuple[int, int]:
        """Return the current position rounded to the movement lattice."""
        sx = int(round(self.x / LATTICE_STEP)) * LATTICE_STEP
        sy = int(round(self.y / LATTICE_STEP)) * LATTICE_STEP
        return sx, sy

    def to_dict(self) -> Dict[str, Any]:
        """Serialise the rider to a JSON-compatible dictionary."""
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

    def _record(self, event: str, order_id: Optional[int]) -> None:
        """Append an entry to the rider's event log.

        The log is capped at ``MAX_LOG_ENTRIES`` to keep memory bounded during
        long runs.
        """
        entry = {
            "tick": globalvar.get_value("tick", 0),
            "event": event,
            "order_id": order_id,
            "rider_id": self.rider_id,
            "x": self.x,
            "y": self.y,
            "state": self.state,
        }
        self.log.append(entry)
        if len(self.log) > MAX_LOG_ENTRIES:
            del self.log[0 : len(self.log) - MAX_LOG_ENTRIES]
        logger.debug("Rider %d: %s (order %s)", self.rider_id, event, order_id)

    def _become_idle(self) -> None:
        """Reset the rider to the idle state and clear the route."""
        self.state = IDLE
        self.special_case = False
        self.path = []

    def _update_special_case(self) -> None:
        """Flag the rider when it stands on a restaurant/customer cell."""
        self.special_case = PathPlanner.is_location((self.x, self.y))

    # ------------------------------------------------------------------ #
    # Movement
    # ------------------------------------------------------------------ #
    def _advance(self) -> bool:
        """Move along ``self.path`` by up to ``speed`` units.

        Returns:
            True if the rider has reached the end of its route.
        """
        remaining = self.speed
        while remaining > 0 and self.path:
            tx, ty = self.path[0]
            dx, dy = tx - self.x, ty - self.y
            dist = abs(dx) + abs(dy)
            if dist <= remaining:
                self.x, self.y = tx, ty
                self.path.pop(0)
                remaining -= dist
            else:
                step = remaining
                if dx != 0:
                    self.x += step if dx > 0 else -step
                else:
                    self.y += step if dy > 0 else -step
                remaining = 0
        self._update_special_case()
        return not self.path

    # ------------------------------------------------------------------ #
    # State transitions
    # ------------------------------------------------------------------ #
    def _accept_order(self, order: Any) -> None:
        """Transition IDLE -> PICKING_UP and plan the route to the restaurant."""
        self.state = PICKING_UP
        order.mark_picking_up()
        self.path = PathPlanner.plan(self.snapped_position(), order.res_pos)
        self._record("accepted_order", order.id)

    def _complete_order(self, order: Any) -> None:
        """Finish the active order and return the rider to IDLE."""
        self._record("delivered_to_customer", order.id)
        order.complete(globalvar.get_value("tick", 0))
        self.orders.pop(0)
        self._become_idle()

    def move(self) -> None:
        """Advance the rider by one tick.

        Handles acceptance of new orders, movement along the planned route,
        pickup arrival (PICKING_UP -> DELIVERING) and delivery completion
        (DELIVERING -> IDLE). Inconsistent states are corrected automatically.
        """
        if not self.orders:
            if self.state != IDLE:
                logger.warning("Rider %d had state %d without orders; resetting.",
                               self.rider_id, self.state)
                self._become_idle()
            return

        if self.state == IDLE:
            self._accept_order(self.orders[0])
            return

        order = self.orders[0]
        if self.state == PICKING_UP:
            if self._advance():
                self._record("arrived_at_merchant", order.id)
                order.mark_delivering()
                self.state = DELIVERING
                self.path = PathPlanner.plan(self.snapped_position(), order.cus_pos)
        elif self.state == DELIVERING:
            if self._advance():
                self._complete_order(order)
        else:
            logger.warning("Rider %d has unknown state %d; resetting.", self.rider_id, self.state)
            self.recover()

    def recover(self) -> None:
        """Rebuild a consistent state after an unexpected error.

        The rider keeps its queued orders, and its route is re-planned toward
        the target that matches its current state.
        """
        if not self.orders:
            self._become_idle()
            return
        order = self.orders[0]
        if self.state == IDLE:
            self.state = PICKING_UP
            order.mark_picking_up()
        target = order.res_pos if self.state == PICKING_UP else order.cus_pos
        self.path = PathPlanner.plan(self.snapped_position(), target)
        self._update_special_case()
