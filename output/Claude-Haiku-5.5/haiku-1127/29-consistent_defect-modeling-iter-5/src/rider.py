"""Rider model: position, state machine, movement and status logging.

State machine:
    Idle (0) -> Picking Up (1) when an order is accepted
    Picking Up (1) -> Delivering (2) on arrival at the restaurant
    Delivering (2) -> Picking Up (1) when a delivery completes and more orders
                                     remain, otherwise -> Idle (0)

Speed note: the recruitment rule creates riders with 10 units/tick, which is the
default used here. The speed can be overridden per rider.
"""

import logging
from typing import Any, Dict, List, Optional, Tuple

import globalvar
from path_planner import PathPlanner

logger = logging.getLogger(__name__)


def _current_time() -> int:
    """Read the current simulation tick from the global store.

    Returns:
        Current tick as an integer.
    """
    return int(globalvar.get_value("time", 0) or 0)


class Rider:
    """A delivery rider that picks up and delivers orders.

    Attributes:
        rider_id: Unique identifier.
        x, y: Current coordinates on the street grid.
        speed: Movement speed in units per tick.
        state: 0 idle, 1 picking up, 2 delivering.
        orders: All orders ever assigned to this rider (delivery history).
        special_case: True while the rider is directly above or below its target.
        log: Chronological status records (dicts with "event", "order_id", ...).
    """

    STATE_IDLE = 0
    STATE_PICKING_UP = 1
    STATE_DELIVERING = 2
    STATE_NAMES = {0: "idle", 1: "picking up", 2: "delivering"}
    START_X = 400
    START_Y = 400
    DEFAULT_SPEED = 10

    def __init__(self, rider_id: int, speed: int = DEFAULT_SPEED) -> None:
        """Create a rider at the default spawn point (400, 400), idle.

        Args:
            rider_id: Unique identifier of the rider.
            speed: Movement speed in units per tick.
        """
        self.rider_id = rider_id
        self.x = self.START_X
        self.y = self.START_Y
        self.speed = speed
        self.state = self.STATE_IDLE
        self.orders: List[Any] = []
        self.special_case = False
        self.log: List[Dict[str, Any]] = []
        self._planner = PathPlanner()
        self._record("spawn", None, _current_time())
        logger.info("Rider %d spawned at (%d, %d)", self.rider_id, self.x, self.y)

    @property
    def position(self) -> Tuple[int, int]:
        """Current (x, y) position."""
        return (self.x, self.y)

    def active_orders(self) -> List[Any]:
        """Return orders that are not yet completed, in assignment order.

        Returns:
            List of uncompleted Order objects.
        """
        return [o for o in self.orders if o.status != "completed"]

    def is_idle(self) -> bool:
        """Check whether the rider can accept a new order.

        Returns:
            True when the rider has no active orders and is in the idle state.
        """
        return self.state == self.STATE_IDLE and not self.active_orders()

    def move(self) -> None:
        """Advance the rider by one tick, applying state transitions.

        Handles order acceptance (idle -> picking up), arrival at the
        restaurant (picking up -> delivering) and delivery completion
        (delivering -> picking up / idle), recording a log entry for each.
        """
        now = _current_time()
        active = self.active_orders()

        if not active:
            self.state = self.STATE_IDLE
            self.special_case = False
            return

        if self.state == self.STATE_IDLE:
            self._accept(active[0], now)
            return

        current = active[0]
        if self.state == self.STATE_PICKING_UP:
            if self._advance_towards(current.restaurant_pos):
                self.state = self.STATE_DELIVERING
                current.status = "delivering"
                self._record("arrived_at_merchant", current.id, now)
                logger.info("Rider %d arrived at restaurant for order %d",
                            self.rider_id, current.id)
        elif self.state == self.STATE_DELIVERING:
            if self._advance_towards(current.customer_pos):
                current.complete(now)
                self._record("delivered_to_customer", current.id, now)
                remaining = self.active_orders()
                if remaining:
                    self._accept(remaining[0], now)
                else:
                    self.state = self.STATE_IDLE
                    self.special_case = False
        else:
            logger.warning("Rider %d had invalid state %s; resetting to idle",
                           self.rider_id, self.state)
            self.state = self.STATE_IDLE

    def _accept(self, order: Any, now: int) -> None:
        """Transition to picking up for the given order.

        Args:
            order: The order being accepted.
            now: Current tick.
        """
        self.state = self.STATE_PICKING_UP
        order.status = "picking_up"
        self._record("accepted_order", order.id, now)

    def _advance_towards(self, target: Tuple[int, int]) -> bool:
        """Move one tick along the street network towards a target.

        Args:
            target: Destination (x, y).

        Returns:
            True if the rider has reached the target after moving.
        """
        tx, ty = target
        self.special_case = self.x == tx and self.y != ty
        self.x, self.y = self._planner.next_position(self.x, self.y, tx, ty, self.speed)
        return (self.x, self.y) == (tx, ty)

    def _record(self, event: str, order_id: Optional[int], now: int) -> None:
        """Append a status record to the rider log.

        Args:
            event: Event name (spawn, accepted_order, arrived_at_merchant,
                delivered_to_customer).
            order_id: Related order id, or None.
            now: Tick at which the event happened.
        """
        self.log.append({
            "event": event,
            "order_id": order_id,
            "time": now,
            "x": self.x,
            "y": self.y,
            "state": self.state,
        })

    def to_dict(self) -> Dict[str, Any]:
        """Serialize the rider to a JSON-compatible dictionary.

        Returns:
            Dictionary describing the rider and its history.
        """
        return {
            "rider_id": self.rider_id,
            "x": self.x,
            "y": self.y,
            "speed": self.speed,
            "state": self.state,
            "special_case": self.special_case,
            "orders": [o.id for o in self.orders],
            "log": list(self.log),
        }
