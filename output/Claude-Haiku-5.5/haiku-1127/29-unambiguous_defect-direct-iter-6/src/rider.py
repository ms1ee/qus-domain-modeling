"""Rider model: state machine, street-grid movement, and event logging.

A rider cycles through three states:

* ``STATE_IDLE`` (0): no active order.
* ``STATE_PICKING_UP`` (1): driving to the restaurant.
* ``STATE_DELIVERING`` (2): driving to the customer.

Each call to ``move()`` advances the rider by one simulation tick. Key events
(order acceptance, arrival at merchant, delivery) are appended to ``log``.
"""

import logging
import random

import config
import globalvar
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

EVENT_SPAWN = "spawn"
EVENT_ACCEPTED = "accepted_order"
EVENT_ARRIVED = "arrived_at_merchant"
EVENT_DELIVERED = "delivered_to_customer"


class Rider:
    """A delivery rider that moves along streets and serves orders.

    Attributes:
        rider_id: Unique integer identifier.
        x: Current x coordinate (0-800).
        y: Current y coordinate (0-800).
        speed: Movement speed in units per tick.
        state: Current state (0 idle, 1 picking up, 2 delivering).
        orders: List of assigned orders that are not yet delivered.
        special_case: True when the rider is at a cell-centre location or
            directly above/below its target.
        log: List of event dictionaries with keys ``event`` and ``order_id``
            (plus ``time``, ``rider_id``, ``x``, ``y``, ``state``).
    """

    def __init__(self, rider_id):
        """Create a rider on a random street point.

        Args:
            rider_id: Unique integer identifier for the rider.
        """
        self.rider_id = int(rider_id)
        self.x, self.y = PathPlanner.random_street_point()
        self.speed = random.choice(config.SPEED_CHOICES)
        self.state = STATE_IDLE
        self.orders = []
        self.special_case = False
        self.log = []
        self.path = []
        self.target = None
        self.current_order = None
        self._progress = 0
        self._record(EVENT_SPAWN, None)
        logger.info("Rider %d spawned at (%d, %d)", self.rider_id, self.x, self.y)

    @property
    def position(self):
        """Return the current ``(x, y)`` position."""
        return (self.x, self.y)

    @property
    def state_name(self):
        """Return a human-readable name for the current state."""
        return STATE_NAMES.get(self.state, "unknown")

    def __repr__(self):
        return (
            f"Rider(id={self.rider_id}, pos=({self.x}, {self.y}), "
            f"state={self.state_name}, orders={len(self.orders)})"
        )

    def to_dict(self):
        """Return a JSON-serialisable snapshot of the rider.

        Returns:
            Dictionary describing the rider and its assigned order IDs.
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

    def move(self):
        """Advance the rider by one tick.

        Starts the next assigned order when idle, moves along the planned
        route, and performs state transitions when the rider reaches the
        restaurant or the customer.
        """
        now = self._now()
        if self.state == STATE_IDLE:
            self._start_next_order(now)
        if self.state == STATE_IDLE:
            return
        if not self.path and self.position != self.target:
            self._plan_to(self.target)
        self._advance()
        self._process_arrivals(now)
        self._update_special_case()

    def recover(self):
        """Reset the rider to a consistent idle state after an internal error.

        Orders that were in progress are returned to the ``assigned`` status
        so they will be restarted on the next tick.
        """
        if self.current_order is not None and self.current_order.status != "completed":
            self.current_order.status = "assigned"
        self.state = STATE_IDLE
        self.path = []
        self.target = None
        self.current_order = None
        self._progress = 0
        self.special_case = False
        logger.warning("Rider %d recovered to idle state", self.rider_id)

    def _now(self):
        """Return the current simulated tick."""
        return globalvar.get_value("tick", 0) or 0

    def _record(self, event, order_id, now=None):
        """Append an event entry to the rider log.

        Args:
            event: Event name.
            order_id: Related order ID, or None.
            now: Tick to record; defaults to the current tick.
        """
        entry = {
            "event": event,
            "order_id": order_id,
            "time": self._now() if now is None else now,
            "rider_id": self.rider_id,
            "x": self.x,
            "y": self.y,
            "state": self.state,
        }
        self.log.append(entry)
        logger.debug("Rider %d event %s order=%s", self.rider_id, event, order_id)

    def _start_next_order(self, now):
        """Begin pickup of the first order with the ``assigned`` status.

        Args:
            now: Current tick.

        Returns:
            True if an order was started, otherwise False.
        """
        for order in self.orders:
            if order.status == "assigned":
                self.current_order = order
                order.mark_picking_up()
                self.state = STATE_PICKING_UP
                self._record(EVENT_ACCEPTED, order.id, now)
                self._plan_to(order.res_pos)
                return True
        return False

    def _plan_to(self, goal):
        """Compute a route from the current position to ``goal``.

        Args:
            goal: Target ``(x, y)`` point.
        """
        self.target = goal
        occupied = {
            rider.position
            for rider in (globalvar.get_value("riders") or [])
            if rider is not self
        }
        self.path = PathPlanner.plan(self.position, goal, occupied)[1:]

    def _advance(self):
        """Move along the planned path using this tick's speed budget."""
        if not self.path:
            self._progress = 0
            return
        self._progress += self.speed
        step = config.LATTICE_STEP
        while self.path and self._progress >= step:
            self.x, self.y = self.path.pop(0)
            self._progress -= step
        if not self.path:
            self._progress = 0

    def _process_arrivals(self, now):
        """Handle arrivals at the restaurant and the customer.

        Args:
            now: Current tick.
        """
        while self.state != STATE_IDLE and not self.path and self.position == self.target:
            if self.state == STATE_PICKING_UP:
                self.state = STATE_DELIVERING
                self.current_order.mark_delivering()
                self._record(EVENT_ARRIVED, self.current_order.id, now)
                self._plan_to(self.current_order.cus_pos)
            else:
                self._deliver(now)

    def _deliver(self, now):
        """Complete the current order and release the rider.

        Args:
            now: Current tick.
        """
        order = self.current_order
        order.complete(now)
        self._record(EVENT_DELIVERED, order.id, now)
        if order in self.orders:
            self.orders.remove(order)
        fee = config.setting("delivery_fee")
        globalvar.set_value("funds", (globalvar.get_value("funds") or 0) + fee)
        self.current_order = None
        self.state = STATE_IDLE
        self.target = None
        self.path = []
        self._progress = 0
        logger.info("Rider %d delivered order %d", self.rider_id, order.id)
        self._start_next_order(now)

    def _update_special_case(self):
        """Refresh the ``special_case`` flag.

        The flag is set when the rider stands on a cell-centre location or
        is directly above or below its target.
        """
        at_location = PathPlanner.is_location(self.position)
        aligned = (
            self.target is not None
            and self.position != self.target
            and (self.x == self.target[0] or self.y == self.target[1])
        )
        self.special_case = at_location or aligned
