"""Rider model: state machine, movement and order processing.

State machine
-------------
* Idle (0) -> Picking up (1): an order is present in ``orders`` (accepted).
* Picking up (1) -> Delivering (2): the rider reaches the restaurant.
* Delivering (2) -> Idle (0): the order is delivered and removed from ``orders``.

Orders queue in ``orders``; the first entry is the active order. Every
state change is appended to ``log`` with the simulated time, position and order
id.
"""

import logging
import math

import config
import globalvar
from path_planner import PathPlanner, is_street_point

logger = logging.getLogger(__name__)

STATE_IDLE = 0
STATE_PICKING_UP = 1
STATE_DELIVERING = 2

STATE_NAMES = {
    STATE_IDLE: "idle",
    STATE_PICKING_UP: "picking up",
    STATE_DELIVERING: "delivering",
}


class Rider:
    """A delivery rider that moves on the street grid and serves orders.

    Attributes:
        rider_id: Unique identifier.
        x: Current x coordinate.
        y: Current y coordinate.
        speed: Distance covered per tick (units/tick).
        state: 0 idle, 1 picking up, 2 delivering.
        orders: Assigned orders, the first being the active one.
        special_case: True while the rider is off the street grid.
        route: Remaining waypoints of the current leg.
        log: List of event dictionaries with keys ``event`` and ``order_id``
            (plus ``time``, ``rider_id``, ``x``, ``y`` and ``state``).
    """

    def __init__(self, rider_id):
        """Create a rider at the spawn point with idle status.

        Args:
            rider_id: Unique rider identifier.
        """
        params = config.PARAMS
        self.rider_id = int(rider_id)
        self.x = int(params["spawn_x"])
        self.y = int(params["spawn_y"])
        self.speed = int(params["rider_speed"])
        self.state = STATE_IDLE
        self.orders = []
        self.special_case = not is_street_point(self.x, self.y)
        self.route = []
        self.log = []
        self._planner = PathPlanner()
        self._record("spawn", None)
        logger.debug("Rider %s spawned at (%s, %s)", self.rider_id, self.x, self.y)

    @property
    def position(self):
        """Current ``(x, y)`` position."""
        return (self.x, self.y)

    @property
    def state_name(self):
        """Human-readable state name."""
        return STATE_NAMES.get(self.state, "unknown")

    def distance_to(self, point):
        """Euclidean distance from the rider to a point.

        Args:
            point: ``(x, y)`` target.

        Returns:
            Distance in units.
        """
        return math.hypot(self.x - point[0], self.y - point[1])

    def current_order(self):
        """Return the active order (first in the queue) or None."""
        return self.orders[0] if self.orders else None

    def move(self):
        """Advance the rider by one tick.

        Handles order acceptance, movement along the planned route, arrival at
        the restaurant and delivery to the customer, logging each transition.
        """
        now = self._now()
        if self.state == STATE_IDLE:
            if not self.orders:
                return
            self._accept_order(self.orders[0], now)

        self._advance()

        while not self.route and self.state != STATE_IDLE and self.orders:
            order = self.orders[0]
            if self.state == STATE_PICKING_UP:
                self._arrive_at_merchant(order, now)
            else:
                self._deliver(order, now)

        self.special_case = not is_street_point(self.x, self.y)

    def to_dict(self):
        """Return a JSON-serialisable representation of the rider."""
        return {
            "rider_id": self.rider_id,
            "x": self.x,
            "y": self.y,
            "speed": self.speed,
            "state": self.state,
            "state_name": self.state_name,
            "order_ids": [order.id for order in self.orders],
            "special_case": self.special_case,
            "log": list(self.log),
        }

    def _now(self):
        """Current simulated tick."""
        return globalvar.get_value("tick", 0)

    def _record(self, event, order_id):
        """Append a state-change entry to the rider log."""
        self.log.append({
            "event": event,
            "order_id": order_id,
            "time": self._now(),
            "rider_id": self.rider_id,
            "x": self.x,
            "y": self.y,
            "state": self.state,
        })

    def _plan_to(self, target):
        """Compute a fresh route from the current position to ``target``."""
        self.route = self._planner.plan(self.position, target)

    def _advance(self):
        """Move along the current route by one tick of speed."""
        if not self.route:
            return
        self.position_tuple, self.route = PathPlanner.step_along(
            self.position, self.route, self.speed)
        self.x, self.y = self.position_tuple
        del self.position_tuple

    def _accept_order(self, order, now):
        """Start the pickup leg for the given order."""
        self.state = STATE_PICKING_UP
        order.status = "picking_up"
        order.accept_time = now
        self._record("accepted_order", order.id)
        self._plan_to(order.res_pos)

    def _arrive_at_merchant(self, order, now):
        """Handle arrival at the restaurant and start the delivery leg."""
        self.state = STATE_DELIVERING
        order.status = "delivering"
        order.pickup_time = now
        self._record("arrived_at_merchant", order.id)
        self._plan_to(order.cus_pos)

    def _deliver(self, order, now):
        """Complete the active order and return the rider to idle."""
        order.complete(now)
        self.orders.remove(order)
        self.state = STATE_IDLE
        self.route = []
        self._record("delivered_to_customer", order.id)
