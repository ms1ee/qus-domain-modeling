"""Rider entity: movement, state transitions and event logging.

State machine:
    idle (0) -> picking up (1) when an order is accepted
    picking up (1) -> delivering (2) on arrival at the restaurant
    delivering (2) -> idle (0) after delivery (or -> picking up for the next
    queued order)

Every transition is recorded in ``rider.log`` as a dict with the keys
``event``, ``order_id``, ``time``, ``x``, ``y`` and ``state``.
"""

import logging

import globalvar
import grid
import order_model
from path_planner import (PathPlanner, STATE_IDLE, STATE_PICKING_UP,
                          STATE_DELIVERING)

logger = logging.getLogger("dispatch.rider")

STATE_NAMES = {
    STATE_IDLE: "idle",
    STATE_PICKING_UP: "picking up",
    STATE_DELIVERING: "delivering",
}
DEFAULT_SPEED = 50


class Rider:
    """A delivery rider that moves on the street grid.

    Attributes:
        rider_id: Unique identifier.
        x: Current x coordinate.
        y: Current y coordinate.
        speed: Movement speed in units per tick.
        state: 0 idle, 1 picking up, 2 delivering.
        orders: Assigned orders, the first one being the active order.
        special_case: True when the rider yielded or is in a special state.
        route: Remaining waypoints of the current leg.
        log: Chronological list of event dictionaries.
        total_distance: Total units travelled.
    """

    def __init__(self, rider_id, x=50, y=50, speed=DEFAULT_SPEED):
        """Create a rider and log its spawn event.

        Args:
            rider_id: Unique identifier.
            x: Initial x coordinate (defaults to a cell center).
            y: Initial y coordinate (defaults to a cell center).
            speed: Movement speed in units per tick, must be positive.

        Raises:
            ValueError: If speed is not positive.
        """
        if int(speed) <= 0:
            raise ValueError("rider speed must be a positive integer")
        self.rider_id = int(rider_id)
        self.x = int(x)
        self.y = int(y)
        self.speed = int(speed)
        self.state = STATE_IDLE
        self.orders = []
        self.special_case = False
        self.route = []
        self.log = []
        self.total_distance = 0
        self._planner = PathPlanner()
        self._record("spawn", None)
        logger.info("Rider #%d spawned at (%d, %d)", self.rider_id,
                    self.x, self.y)

    @property
    def position(self):
        """Current position as a tuple ``(x, y)``."""
        return (self.x, self.y)

    @property
    def state_name(self):
        """Human-readable name of the current state."""
        return STATE_NAMES.get(self.state, "unknown")

    def _now(self):
        """Return the current simulation tick."""
        return globalvar.get_value("tick", 0)

    def _all_riders(self):
        """Return the list of all riders from global storage."""
        return globalvar.get_value("riders") or []

    def _record(self, event, order_id):
        """Append an event entry to the rider log.

        Args:
            event: Event name such as ``accepted_order``.
            order_id: Related order identifier, or None.
        """
        self.log.append({
            "event": event,
            "order_id": order_id,
            "time": self._now(),
            "x": self.x,
            "y": self.y,
            "state": self.state,
        })

    def _plan_to(self, target, order):
        """Plan the route to ``target`` and add its length to the order."""
        points = self._planner.plan(self.position, target)
        order.distance += grid.path_length(self.position, points)
        self.route = points

    def _begin_pickup(self):
        """Start the pickup leg for the first order in the queue."""
        order = self.orders[0]
        self.state = STATE_PICKING_UP
        order.status = order_model.PICKING_UP
        self._plan_to(order.res_grid, order)
        self._record("accepted_order", order.id)
        logger.info("Rider #%d accepted order #%d", self.rider_id, order.id)

    def _finish_leg(self):
        """Handle arrival at the current leg destination."""
        if not self.orders:
            self.state = STATE_IDLE
            self.route = []
            return
        order = self.orders[0]
        if self.state == STATE_PICKING_UP:
            self.state = STATE_DELIVERING
            order.status = order_model.DELIVERING
            self._plan_to(order.cus_grid, order)
            self._record("arrived_at_merchant", order.id)
            logger.info("Rider #%d picked up order #%d",
                        self.rider_id, order.id)
        elif self.state == STATE_DELIVERING:
            self.orders.pop(0)
            order.complete(self._now())
            self._record("delivered_to_customer", order.id)
            logger.info("Rider #%d delivered order #%d",
                        self.rider_id, order.id)
            if self.orders:
                self._begin_pickup()
            else:
                self.state = STATE_IDLE
                self.route = []
                self.special_case = False

    def _advance(self):
        """Move along the current route using this tick's speed budget."""
        budget = self.speed
        self.special_case = False
        riders = self._all_riders()
        while budget > 0 and self.route:
            target = self.route[0]
            nx, ny, moved = self._planner.step(self.x, self.y, target, budget)
            if moved == 0:
                self.route.pop(0)
                continue
            if self._planner.is_blocked(self, (nx, ny), riders):
                self.special_case = True
                logger.debug("Rider #%d yielded at (%d, %d)",
                             self.rider_id, self.x, self.y)
                return
            self.x, self.y = nx, ny
            self.total_distance += moved
            budget -= moved
            if (self.x, self.y) == target:
                self.route.pop(0)

    def move(self):
        """Advance the rider by one tick.

        Handles the idle-to-picking-up transition when an order is assigned,
        moves along the planned route, and performs arrival transitions
        (restaurant and customer) when a leg completes.
        """
        if self.state == STATE_IDLE:
            if not self.orders:
                self.special_case = False
                return
            self._begin_pickup()
        self._advance()
        while not self.route and self.state != STATE_IDLE:
            self._finish_leg()

    def to_dict(self):
        """Return a JSON-serialisable representation of the rider."""
        return {
            "rider_id": self.rider_id,
            "x": self.x,
            "y": self.y,
            "speed": self.speed,
            "state": self.state,
            "state_name": self.state_name,
            "orders": [order.id for order in self.orders],
            "special_case": self.special_case,
            "total_distance": self.total_distance,
            "log": list(self.log),
        }
