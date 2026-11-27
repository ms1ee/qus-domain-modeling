"""Rider model: state machine, movement along planned routes, and logging.

State transitions:
    Idle (0) -> Picking up (1) when an order is accepted.
    Picking up (1) -> Delivering (2) on arrival at the restaurant.
    Delivering (2) -> Idle (0) on delivery to the customer.

Riders do not reserve map cells, so they never block one another; this
design avoids path-conflict deadlocks by construction.
"""

import logging

from globalvar import get_value
from grid_map import Point
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

DEFAULT_X = 435
DEFAULT_Y = 385
DEFAULT_SPEED = 10

_PLANNER = PathPlanner()


def _current_tick():
    """Return the current simulation tick from the global store."""
    return get_value("current_tick", 0)


class Rider:
    """A delivery rider that moves on the grid and serves orders.

    Attributes:
        rider_id: Unique integer identifier.
        x: Current x coordinate.
        y: Current y coordinate.
        speed: Movement speed in units per tick.
        state: 0 idle, 1 picking up, 2 delivering.
        orders: List of assigned Order objects (the first is active).
        special_case: True while moving in a straight line toward a target
            located directly above, below, left or right of the rider.
        log: List of dict entries describing status changes.
        route: The currently planned Route, or None.
    """

    def __init__(self, rider_id, x=DEFAULT_X, y=DEFAULT_Y,
                 speed=DEFAULT_SPEED):
        """Create a rider and record its spawn event.

        Args:
            rider_id: Unique identifier.
            x: Initial x coordinate.
            y: Initial y coordinate.
            speed: Movement speed in units per tick.
        """
        self.rider_id = int(rider_id)
        self.x = int(x)
        self.y = int(y)
        self.speed = int(speed)
        self.state = STATE_IDLE
        self.orders = []
        self.special_case = False
        self.log = []
        self.route = None
        self._waypoints = []
        self._record("spawn", None)

    def position(self):
        """Return the current position as a Point."""
        return Point(self.x, self.y)

    def current_target(self):
        """Return the Point the rider is currently heading to.

        Returns:
            Restaurant point while picking up, customer point while
            delivering, or None when the rider has no orders.
        """
        if not self.orders:
            return None
        order = self.orders[0]
        if self.state == STATE_DELIVERING:
            return Point(order.customer_x, order.customer_y)
        return Point(order.restaurant_x, order.restaurant_y)

    def move(self):
        """Advance the rider by one tick.

        Handles state transitions, movement by ``speed`` units along the
        planned route, arrival detection and order completion. All status
        changes are recorded in ``self.log``.
        """
        if self.orders and self.orders[0].status == "completed":
            self.orders.pop(0)

        if not self.orders:
            if self.state != STATE_IDLE:
                logger.warning("Rider %d had no orders while state=%d; "
                               "resetting to idle.", self.rider_id,
                               self.state)
                self.state = STATE_IDLE
                self.reset_route()
            return

        order = self.orders[0]
        if self.state == STATE_IDLE:
            self.state = STATE_PICKING_UP
            self._record("accepted_order", order.id)
            self._plan_to(self.current_target())

        self._advance(self.speed)

        if self.state == STATE_PICKING_UP:
            if self._at_target():
                self.state = STATE_DELIVERING
                self._record("arrived_at_merchant", order.id)
                self._plan_to(self.current_target())
        elif self.state == STATE_DELIVERING and self._at_target():
            self._complete_order()

    def resync(self):
        """Repair an inconsistent movement state.

        Returns:
            True if the rider state or route was changed.
        """
        if not self.orders:
            if self.state != STATE_IDLE:
                self.state = STATE_IDLE
                self.reset_route()
                return True
            return False
        if (self.state != STATE_IDLE and not self._waypoints
                and not self._at_target()):
            self._plan_to(self.current_target())
            return True
        return False

    def reset_route(self):
        """Clear the planned route and the straight-line flag."""
        self.route = None
        self._waypoints = []
        self.special_case = False

    def to_dict(self):
        """Return a JSON-serialisable snapshot of the rider."""
        return {
            "rider_id": self.rider_id,
            "x": self.x,
            "y": self.y,
            "speed": self.speed,
            "state": self.state,
            "special_case": self.special_case,
            "orders": [order.id for order in self.orders],
        }

    def _record(self, event, order_id):
        """Append a status-change entry to the rider log."""
        entry = {
            "event": event,
            "order_id": order_id,
            "rider_id": self.rider_id,
            "tick": _current_tick(),
            "x": self.x,
            "y": self.y,
            "state": self.state,
        }
        self.log.append(entry)
        logger.info("Rider %d %s (order %s) at (%d, %d) tick %d",
                    self.rider_id, event, order_id, self.x, self.y,
                    entry["tick"])

    def _plan_to(self, goal):
        """Plan a route from the current position to ``goal``."""
        if goal is None:
            self.reset_route()
            return
        start = self.position()
        self.route = _PLANNER.plan(start, goal)
        self._waypoints = list(self.route.waypoints[1:])
        self.special_case = (start != goal
                             and (start.x == goal.x or start.y == goal.y))

    def _at_target(self):
        """Return True if the rider stands on its current target."""
        target = self.current_target()
        if target is None:
            return False
        return not self._waypoints and (self.x, self.y) == (target.x,
                                                            target.y)

    def _advance(self, budget):
        """Move along the waypoints using up to ``budget`` units.

        Segments are axis-aligned, so each step changes only one coordinate.
        """
        budget = int(budget)
        while budget > 0 and self._waypoints:
            nxt = self._waypoints[0]
            dx = nxt.x - self.x
            dy = nxt.y - self.y
            if dx == 0 and dy == 0:
                self._waypoints.pop(0)
                continue
            if dx != 0:
                step = min(budget, abs(dx))
                self.x += step if dx > 0 else -step
            else:
                step = min(budget, abs(dy))
                self.y += step if dy > 0 else -step
            budget -= step
            if (self.x, self.y) == (nxt.x, nxt.y):
                self._waypoints.pop(0)

    def _complete_order(self):
        """Finish the active order and return the rider to idle."""
        order = self.orders.pop(0)
        order.complete(_current_tick())
        self._record("delivered_to_customer", order.id)
        self.state = STATE_IDLE
        self.reset_route()
