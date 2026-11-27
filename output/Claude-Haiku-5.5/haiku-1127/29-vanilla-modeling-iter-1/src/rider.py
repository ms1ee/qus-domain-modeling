"""Rider model: state machine, movement and order execution.

State machine:
    IDLE (0) -> PICKING_UP (1): a new order is present when move() runs.
    PICKING_UP (1) -> DELIVERING (2): the rider reaches the restaurant centre.
    DELIVERING (2) -> IDLE (0) (or PICKING_UP for the next queued order):
        the rider reaches the customer centre and the order completes.

Every transition appends an entry to ``Rider.log``.
"""

import logging
from typing import Any, Dict, Iterable, List, Optional, Tuple

import globalvar
from path_planner import PathPlanner

logger = logging.getLogger(__name__)

Point = Tuple[int, int]

_PLANNER = PathPlanner()


class Rider:
    """A delivery rider that moves on the street grid and executes orders.

    Attributes:
        rider_id: Unique identifier.
        x, y: Current position in units.
        speed: Units moved per tick.
        state: 0 = idle, 1 = picking up, 2 = delivering.
        orders: Queue of assigned orders; orders[0] is the active order.
        special_case: True when the rider is aligned with its target or blocked.
        log: List of event dictionaries with keys "event" and "order_id".
        blocked_ticks: Consecutive ticks in which the rider could not move.
        distance_travelled: Total units moved.
    """

    STATE_IDLE = 0
    STATE_PICKING_UP = 1
    STATE_DELIVERING = 2
    STATE_NAMES = {0: "idle", 1: "picking up", 2: "delivering"}
    BLOCKED_TICKS_BEFORE_DETOUR = 2

    def __init__(self, rider_id: int) -> None:
        """Create a new idle rider at the configured start position.

        Args:
            rider_id: Unique identifier assigned by the system.

        Raises:
            ValueError: If the configured speed is not positive.
        """
        config = globalvar.get_value("config", globalvar.DEFAULT_CONFIG)
        start = config.get("rider_start", globalvar.DEFAULT_CONFIG["rider_start"])
        self.rider_id = int(rider_id)
        self.x = int(start[0])
        self.y = int(start[1])
        self.speed = int(config.get("rider_speed", globalvar.DEFAULT_CONFIG["rider_speed"]))
        if self.speed <= 0:
            raise ValueError("rider speed must be a positive integer")
        self.state = self.STATE_IDLE
        self.orders: List[Any] = []
        self.special_case = False
        self.log: List[Dict[str, Any]] = []
        self.blocked_ticks = 0
        self.distance_travelled = 0
        self._record("spawn", None)

    # ------------------------------------------------------------------
    # Properties and helpers
    # ------------------------------------------------------------------
    @property
    def position(self) -> Point:
        """Current position as a tuple."""
        return self.x, self.y

    @property
    def state_name(self) -> str:
        """Human readable name of the current state."""
        return self.STATE_NAMES.get(self.state, "unknown")

    @property
    def is_idle(self) -> bool:
        """True when the rider has no state work and no orders."""
        return self.state == self.STATE_IDLE and not self.orders

    def _record(self, event: str, order_id: Optional[int]) -> None:
        """Append an event entry to the rider log.

        Args:
            event: Event name (spawn, accepted_order, arrived_at_merchant,
                delivered_to_customer).
            order_id: Related order ID or None.
        """
        entry = {
            "event": event,
            "order_id": order_id,
            "rider_id": self.rider_id,
            "tick": int(globalvar.get_value("current_tick", 0)),
            "x": self.x,
            "y": self.y,
            "state": self.state,
        }
        self.log.append(entry)
        logger.debug("Rider %d: %s (order %s)", self.rider_id, event, order_id)

    def _target(self) -> Point:
        """Return the grid centre the rider is currently heading to."""
        order = self.orders[0]
        if self.state == self.STATE_PICKING_UP:
            return order.res_center
        return order.cus_center

    def _complete_current_order(self, tick: int) -> None:
        """Finish the active order and remove it from the rider's queue."""
        order = self.orders.pop(0)
        order.complete(tick)
        self._record("delivered_to_customer", order.id)

    # ------------------------------------------------------------------
    # Simulation
    # ------------------------------------------------------------------
    def move(self, occupied: Optional[Iterable[Point]] = None) -> None:
        """Advance the rider by one tick.

        Performs up to ``speed`` unit steps toward the current target, applying
        state transitions when targets are reached. Positions in ``occupied``
        are avoided; a rider blocked for several ticks changes its axis
        preference to break deadlocks.

        Args:
            occupied: Positions currently held by other riders.
        """
        blocked_cells = set(occupied) if occupied is not None else set()
        tick = int(globalvar.get_value("current_tick", 0))

        if not self.orders:
            self.state = self.STATE_IDLE
            self.special_case = False
            self.blocked_ticks = 0
            return

        if self.state == self.STATE_IDLE:
            self.state = self.STATE_PICKING_UP
            self._record("accepted_order", self.orders[0].id)

        budget = self.speed
        moved = False
        while self.orders:
            target = self._target()
            if self.position == target:
                if self.state == self.STATE_PICKING_UP:
                    order = self.orders[0]
                    self.state = self.STATE_DELIVERING
                    order.mark_picked_up(tick)
                    self._record("arrived_at_merchant", order.id)
                    continue
                self._complete_current_order(tick)
                if self.orders:
                    self.state = self.STATE_PICKING_UP
                    self._record("accepted_order", self.orders[0].id)
                else:
                    self.state = self.STATE_IDLE
                continue

            if budget <= 0:
                break
            prefer_vertical = _PLANNER.prefers_vertical(self.position)
            if self.blocked_ticks >= self.BLOCKED_TICKS_BEFORE_DETOUR:
                prefer_vertical = not prefer_vertical
            nxt = _PLANNER.next_step(self.position, target, blocked_cells,
                                     prefer_vertical=prefer_vertical)
            if nxt is None:
                break
            self.x, self.y = nxt
            self.distance_travelled += 1
            budget -= 1
            moved = True

        if self.orders:
            target = self._target()
            at_target = self.position == target
            aligned = self.x == target[0] or self.y == target[1]
            if moved or at_target:
                self.blocked_ticks = 0
            else:
                self.blocked_ticks += 1
            self.special_case = aligned or self.blocked_ticks > 0
        else:
            self.blocked_ticks = 0
            self.special_case = False

    def to_dict(self) -> Dict[str, Any]:
        """Return a JSON-serialisable representation of the rider."""
        return {
            "rider_id": self.rider_id,
            "x": self.x,
            "y": self.y,
            "speed": self.speed,
            "state": self.state,
            "orders": [order.id for order in self.orders],
            "special_case": self.special_case,
        }
