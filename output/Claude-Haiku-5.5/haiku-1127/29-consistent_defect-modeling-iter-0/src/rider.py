"""Rider model: state machine, movement and delivery history.

Rider states (see :mod:`config`):
    0 idle, 1 picking up (en route to restaurant), 2 delivering.

Transitions:
    idle -> picking up        when an active order is present (accepted_order)
    picking up -> delivering  on arrival at the restaurant (arrived_at_merchant)
    delivering -> picking up  when an order is delivered and another is queued
    delivering -> idle        when an order is delivered and none are queued
                              (delivered_to_customer)
"""

import logging
from typing import Any, Dict, List, Optional, Tuple

import globalvar
from config import (ORDER_COMPLETED, RIDER_SPEED, RIDER_START_X,
                    RIDER_START_Y, STATE_DELIVERING, STATE_IDLE,
                    STATE_PICKING_UP)
from path_planner import PathPlanner

logger = logging.getLogger(__name__)

_planner = PathPlanner()


class Rider:
    """A delivery rider that moves along streets and serves orders.

    Attributes:
        rider_id: Unique identifier.
        x, y: Current location.
        speed: Movement speed in units per tick.
        state: Current state enum (0 idle, 1 picking up, 2 delivering).
        orders: Every order ever assigned, including completed history.
        special_case: True when directly above or below the current target.
        log: Event records with keys ``time``, ``event``, ``order_id``, etc.
        distance_travelled: Total distance moved by this rider.

    Note:
        Riders are not blocked by one another, so no path conflicts arise.
        Movement is sequential and always makes progress toward a target
        that is a grid intersection, so no deadlock is possible.
    """

    def __init__(self, rider_id: int) -> None:
        """Create a rider at the default road position in the idle state.

        Args:
            rider_id: Unique identifier for the rider.
        """
        self.rider_id = int(rider_id)
        self.x = RIDER_START_X
        self.y = RIDER_START_Y
        self.speed = RIDER_SPEED
        self.state = STATE_IDLE
        self.orders: List[Any] = []
        self.special_case = False
        self.log: List[Dict[str, Any]] = []
        self.distance_travelled = 0
        self._record("spawn")

    # ------------------------------------------------------------------
    # Properties
    # ------------------------------------------------------------------
    @property
    def position(self) -> Tuple[int, int]:
        """Current ``(x, y)`` location."""
        return (self.x, self.y)

    @property
    def active_orders(self) -> List[Any]:
        """Assigned orders that have not yet been completed."""
        return [o for o in self.orders if o.status != ORDER_COMPLETED]

    @property
    def current_order(self) -> Optional[Any]:
        """The order currently being served (oldest active), or None."""
        active = self.active_orders
        return active[0] if active else None

    @property
    def is_idle(self) -> bool:
        """True when the rider is idle and has no active orders."""
        return self.state == STATE_IDLE and not self.active_orders

    # ------------------------------------------------------------------
    # Simulation
    # ------------------------------------------------------------------
    def move(self) -> None:
        """Advance the rider by one tick.

        Handles state transitions, arrival events and movement along streets.
        """
        if self.state == STATE_IDLE:
            order = self.current_order
            if order is None:
                return
            self._start_pickup(order)

        self._process_arrivals()
        if self.state == STATE_IDLE:
            return

        order = self.current_order
        if order is None:
            self.state = STATE_IDLE
            return

        tx, ty = self._target_for(order)
        nx, ny, travelled = _planner.next_position(
            self.x, self.y, tx, ty, self.speed)
        self.x, self.y = nx, ny
        if travelled:
            order.distance += travelled
            self.distance_travelled += travelled
        self.special_case = _planner.is_directly_above_or_below(
            self.x, self.y, tx, ty)

        self._process_arrivals()

    def repair_state(self) -> None:
        """Restore a consistent state after an unexpected exception."""
        order = self.current_order
        if order is None:
            self.state = STATE_IDLE
        elif self.state not in (STATE_PICKING_UP, STATE_DELIVERING):
            self.state = STATE_PICKING_UP
        logger.warning("Rider %s state repaired to %s",
                       self.rider_id, self.state)

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
            "distance_travelled": self.distance_travelled,
            "log": list(self.log),
        }

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------
    def _now(self) -> int:
        """Return the current simulated tick."""
        now = globalvar.get_value("simulated_time")
        return now if now is not None else 0

    def _record(self, event: str, order_id: Optional[int] = None) -> None:
        """Append an entry describing a key moment to the rider log."""
        self.log.append({
            "time": self._now(),
            "event": event,
            "order_id": order_id,
            "rider_id": self.rider_id,
            "x": self.x,
            "y": self.y,
            "state": self.state,
        })

    def _start_pickup(self, order: Any) -> None:
        """Transition to the picking-up state for ``order``."""
        self.state = STATE_PICKING_UP
        self._record("accepted_order", order.id)

    def _target_for(self, order: Any) -> Tuple[int, int]:
        """Return the destination for the rider's current state."""
        if self.state == STATE_PICKING_UP:
            return order.res_pos
        return order.cus_pos

    def _process_arrivals(self) -> None:
        """Apply state transitions for every destination reached right now."""
        while self.state != STATE_IDLE:
            order = self.current_order
            if order is None:
                self.state = STATE_IDLE
                break
            if self.position != self._target_for(order):
                break
            if self.state == STATE_PICKING_UP:
                self.state = STATE_DELIVERING
                self._record("arrived_at_merchant", order.id)
            elif self.state == STATE_DELIVERING:
                order.complete(self._now())
                self._record("delivered_to_customer", order.id)
                next_order = self.current_order
                if next_order is None:
                    self.state = STATE_IDLE
                else:
                    self._start_pickup(next_order)
            else:
                break
