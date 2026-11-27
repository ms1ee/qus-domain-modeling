"""Rider model: state machine, grid movement and status-change logging.

Rider states:
    0 - idle (available)
    1 - picking up (travelling to the restaurant)
    2 - delivering (travelling to the customer)

Each :meth:`Rider.move` call advances the rider by one tick. State
transitions and their log entries happen inside :meth:`Rider.move`.
"""

import logging

import globalvar
from order_model import Order
from path_planner import PathPlanner

logger = logging.getLogger(__name__)

IDLE = 0
PICKING_UP = 1
DELIVERING = 2

STATE_NAMES = {
    IDLE: "idle",
    PICKING_UP: "picking up",
    DELIVERING: "delivering",
}

DEFAULT_SPEED = 10
DEFAULT_X = 435
DEFAULT_Y = 385


def _now():
    """Return the current simulation tick from the global store."""
    return globalvar.get_value("current_time", 0)


class Rider:
    """A delivery rider that moves on the street grid.

    Attributes:
        rider_id: Unique identifier.
        x: Current X coordinate.
        y: Current Y coordinate.
        speed: Movement budget in units per tick.
        state: 0 (idle), 1 (picking up) or 2 (delivering).
        orders: Assigned orders; ``orders[0]`` is the active order.
        special_case: True while following an off-street access route.
        log: List of status-change dictionaries with keys ``event``,
            ``order_id``, ``time``, ``x``, ``y`` and ``state``.
        waypoints: Remaining points of the current route.
        planner: The :class:`PathPlanner` used for route computation.
    """

    def __init__(self, rider_id, x=DEFAULT_X, y=DEFAULT_Y, speed=DEFAULT_SPEED):
        """Create a rider and log its spawn event.

        Args:
            rider_id: Unique rider identifier.
            x: Initial X coordinate (default 435).
            y: Initial Y coordinate (default 385).
            speed: Movement speed in units per tick (default 10).
        """
        self.rider_id = rider_id
        self.x = x
        self.y = y
        self.speed = speed
        self.state = IDLE
        self.orders = []
        self.special_case = False
        self.log = []
        self.waypoints = []
        self.planner = PathPlanner()
        self.log_event("spawn")

    @property
    def position(self):
        """Return the current position as a tuple ``(x, y)``."""
        return (self.x, self.y)

    @property
    def state_name(self):
        """Return a human-readable name for the current state."""
        return STATE_NAMES.get(self.state, "unknown")

    def log_event(self, event, order_id=None):
        """Append a status-change entry to the rider's log.

        Args:
            event: Event name (spawn, accepted_order, arrived_at_merchant,
                delivered_to_customer).
            order_id: Related order ID, or None.

        Returns:
            The created log entry dictionary.
        """
        entry = {
            "event": event,
            "order_id": order_id,
            "time": _now(),
            "x": self.x,
            "y": self.y,
            "state": self.state,
        }
        self.log.append(entry)
        logger.debug("Rider %d: %s (order %s) at (%d, %d)",
                     self.rider_id, event, order_id, self.x, self.y)
        return entry

    def move(self):
        """Advance the rider by one tick.

        Handles the state machine:
            idle with orders -> picking up (logs ``accepted_order``);
            picking up at restaurant -> delivering (logs
            ``arrived_at_merchant``);
            delivering at customer -> idle, or picking up the next order
            (logs ``delivered_to_customer``).
        """
        if self.state == IDLE:
            if not self.orders:
                return
            self._begin_pickup()
        elif not self.orders:
            logger.warning("Rider %d had state %d without orders; resetting",
                           self.rider_id, self.state)
            self._reset_to_idle()
            return

        self._advance(self.speed)
        self._check_arrival()

    def _begin_pickup(self):
        """Start the pickup leg for the first assigned order."""
        order = self.orders[0]
        self.state = PICKING_UP
        order.set_status(Order.PICKING_UP)
        self.log_event("accepted_order", order.id)
        self._plan_route(order.restaurant_pos)

    def _plan_route(self, target, count_distance=True):
        """Plan a route from the current position to ``target``.

        Args:
            target: Destination ``(x, y)``.
            count_distance: Whether to add the route length to the active
                order's distance.
        """
        route = self.planner.plan(self.position, target, self.speed)
        self.waypoints = list(route.waypoints)
        self.special_case = route.special_case
        if count_distance and self.orders:
            self.orders[0].add_distance(route.total_distance)

    def _advance(self, budget):
        """Spend ``budget`` units of movement along the planned waypoints.

        Each segment is axis-aligned, so only one coordinate changes per
        step. Waypoints are consumed as they are reached.

        Args:
            budget: Maximum distance to travel this tick.
        """
        while budget > 0 and self.waypoints:
            tx, ty = self.waypoints[0]
            dx = tx - self.x
            dy = ty - self.y
            if dx == 0 and dy == 0:
                self.waypoints.pop(0)
                continue
            if dx != 0:
                step = min(budget, abs(dx))
                self.x += step if dx > 0 else -step
            else:
                step = min(budget, abs(dy))
                self.y += step if dy > 0 else -step
            budget -= step
            if self.x == tx and self.y == ty:
                self.waypoints.pop(0)

    def _check_arrival(self):
        """Apply state transitions when the rider has reached a target."""
        if self.waypoints or not self.orders:
            return
        order = self.orders[0]
        if self.state == PICKING_UP:
            if self.position != order.restaurant_pos:
                # Recovery: route was lost, replan without double-counting.
                self._plan_route(order.restaurant_pos, count_distance=False)
                return
            self.state = DELIVERING
            order.set_status(Order.DELIVERING)
            self.log_event("arrived_at_merchant", order.id)
            self._plan_route(order.customer_pos)
            self._check_arrival()
        elif self.state == DELIVERING:
            if self.position != order.customer_pos:
                self._plan_route(order.customer_pos, count_distance=False)
                return
            self._complete_current_order()

    def _complete_current_order(self):
        """Finish the active order and release the rider."""
        order = self.orders.pop(0)
        order.complete(_now())
        self.log_event("delivered_to_customer", order.id)
        if self.orders:
            self._begin_pickup()
            self._check_arrival()
        else:
            self._reset_to_idle()

    def _reset_to_idle(self):
        """Return the rider to the idle state and clear its route."""
        self.state = IDLE
        self.waypoints = []
        self.special_case = False

    def to_dict(self):
        """Return a JSON-serialisable representation of the rider.

        Returns:
            Dictionary of rider attributes.
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
