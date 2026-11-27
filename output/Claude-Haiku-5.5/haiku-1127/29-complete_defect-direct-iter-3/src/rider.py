"""Rider model: state machine, movement and event logging."""

import logging

import globalvar
from path_planner import (MAX_WAIT_TICKS, PathPlanner, validate_coordinate)

logger = logging.getLogger(__name__)

IDLE = 0
PICKING_UP = 1
DELIVERING = 2

STATE_NAMES = {
    IDLE: "idle",
    PICKING_UP: "picking up",
    DELIVERING: "delivering",
}

DEFAULT_START_X = 50
DEFAULT_START_Y = 50
DEFAULT_SPEED = 50

_PLANNER = PathPlanner()


def _now():
    """Return the current simulated tick from the global store."""
    return globalvar.get_value("tick", 0)


class Rider:
    """A delivery rider that moves on the street grid and serves orders.

    Orders are assigned by appending them to ``orders``. The first order in
    the list is the active one. Each call to ``move`` advances the rider by one
    tick and applies state transitions:

    * Idle (0) -> Picking up (1): a new order is present; ``accepted_order``.
    * Picking up (1) -> Delivering (2): restaurant reached; ``arrived_at_merchant``.
    * Delivering (2) -> Idle (0): customer reached; ``delivered_to_customer``.

    Attributes:
        rider_id (int): Unique identifier.
        x (int): Current x coordinate (0-800).
        y (int): Current y coordinate (0-800).
        speed (int): Movement speed in units per tick.
        state (int): 0 idle, 1 picking up, 2 delivering.
        orders (list): Assigned orders, active order first.
        special_case (bool): True when aligned with the target or waiting.
        log (list): Event dictionaries with keys "event" and "order_id".
    """

    def __init__(self, rider_id, x=DEFAULT_START_X, y=DEFAULT_START_Y,
                 speed=DEFAULT_SPEED):
        """Create a rider in the idle state and log its spawn event.

        Args:
            rider_id: Unique integer identifier.
            x: Starting x coordinate (0-800).
            y: Starting y coordinate (0-800).
            speed: Positive integer units per tick.

        Raises:
            TypeError: If ``rider_id`` or ``speed`` has the wrong type.
            ValueError: If ``speed`` is not positive or coordinates are invalid.
        """
        if isinstance(rider_id, bool) or not isinstance(rider_id, int):
            raise TypeError("rider_id must be an integer")
        if isinstance(speed, bool) or not isinstance(speed, int) or speed <= 0:
            raise ValueError("speed must be a positive integer")
        validate_coordinate(x, "x")
        validate_coordinate(y, "y")
        self.rider_id = rider_id
        self.x = x
        self.y = y
        self.speed = speed
        self.state = IDLE
        self.orders = []
        self.special_case = False
        self.wait_ticks = 0
        self.log = []
        self._record("spawn", None)

    @property
    def position(self):
        """Return the current position as an ``(x, y)`` tuple."""
        return (self.x, self.y)

    @property
    def state_name(self):
        """Return the human-readable name of the current state."""
        return STATE_NAMES.get(self.state, "unknown")

    def current_order(self):
        """Return the active order, or None when the rider has no orders."""
        return self.orders[0] if self.orders else None

    def move(self):
        """Advance the rider by one tick and apply state transitions.

        Movement follows the street grid. Blocked positions caused by other
        riders are avoided by choosing the alternative corner route; after
        ``MAX_WAIT_TICKS`` waits the rider yields and proceeds anyway to avoid
        deadlock.
        """
        order = self.current_order()
        if order is None:
            self.state = IDLE
            self._reset_flags()
            return

        if self.state == IDLE:
            self.state = PICKING_UP
            order.status = "picking_up"
            self._record("accepted_order", order.id)

        if self.state == PICKING_UP:
            if self._advance_towards(order.res_pos):
                self.state = DELIVERING
                order.status = "delivering"
                self._reset_flags()
                self._record("arrived_at_merchant", order.id)
        elif self.state == DELIVERING:
            if self._advance_towards(order.cus_pos):
                self._complete_current_order()

    def recover(self):
        """Reset the rider to a consistent idle state after an exception.

        Orders are preserved so that the rider can be re-dispatched on the
        next tick.
        """
        logger.warning("Recovering rider #%s to idle state", self.rider_id)
        self.state = IDLE
        self._reset_flags()

    def to_dict(self):
        """Return a JSON-serialisable snapshot of the rider."""
        return {
            "rider_id": self.rider_id,
            "x": self.x,
            "y": self.y,
            "speed": self.speed,
            "state": self.state_name,
            "order_ids": [order.id for order in self.orders],
            "special_case": self.special_case,
            "log": list(self.log),
        }

    def _advance_towards(self, goal):
        """Move one tick towards ``goal`` and report whether it was reached.

        Args:
            goal: Target ``(x, y)`` position.

        Returns:
            True when the rider stands on ``goal`` after this tick.
        """
        if self.position == goal:
            self._reset_flags()
            return True

        ignore_block = self.wait_ticks >= MAX_WAIT_TICKS
        new_x, new_y, waiting = _PLANNER.next_position(
            self.position, goal, self.speed, self._blocked_positions(),
            ignore_block)
        if waiting:
            self.wait_ticks += 1
            self.special_case = True
            return False

        if ignore_block:
            logger.info("Rider #%s yields override to avoid deadlock",
                        self.rider_id)
        self.x, self.y = new_x, new_y
        self.wait_ticks = 0
        # Special case: rider is directly above/below or beside the target.
        self.special_case = (ignore_block or self.x == goal[0]
                             or self.y == goal[1])
        return self.position == goal

    def _blocked_positions(self):
        """Return positions occupied by all other riders."""
        positions = set()
        for other in globalvar.get_value("riders") or []:
            if other is not self:
                positions.add(other.position)
        return positions

    def _complete_current_order(self):
        """Finish the active order, credit funds and return to idle."""
        order = self.orders.pop(0)
        order.complete(_now())
        funds = globalvar.get_value("funds", 0)
        globalvar.set_value("funds", funds + order.fee)
        self._record("delivered_to_customer", order.id)
        self.state = IDLE
        self._reset_flags()

    def _reset_flags(self):
        """Clear the waiting and special-case flags."""
        self.wait_ticks = 0
        self.special_case = False

    def _record(self, event, order_id):
        """Append an event entry to the rider log.

        Args:
            event: One of "spawn", "accepted_order", "arrived_at_merchant",
                or "delivered_to_customer".
            order_id: Related order ID, or None.
        """
        entry = {
            "event": event,
            "order_id": order_id,
            "tick": _now(),
            "rider_id": self.rider_id,
            "x": self.x,
            "y": self.y,
            "state": self.state_name,
        }
        self.log.append(entry)
        logger.debug("Rider #%s event %s order=%s", self.rider_id, event,
                     order_id)
