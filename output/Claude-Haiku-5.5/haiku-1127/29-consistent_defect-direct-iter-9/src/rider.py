"""Rider model: state machine, street movement, and event logging.

State machine:
    IDLE (0)        -> PICKING_UP (1) when an order is accepted
    PICKING_UP (1)  -> DELIVERING (2) on arrival at the restaurant
    DELIVERING (2)  -> PICKING_UP (1) when a delivery completes and more
                                       orders remain, otherwise IDLE (0)

Riders travel only along streets. Riders do not block each other, so
streets are shared and no lock-based deadlock can occur.
"""

import logging
import math

import globalvar
from path_planner import PathPlanner, is_intersection, route_length

logger = logging.getLogger("dispatch.rider")

IDLE = 0
PICKING_UP = 1
DELIVERING = 2
STATE_NAMES = {IDLE: "idle", PICKING_UP: "picking up", DELIVERING: "delivering"}

DEFAULT_SPEED = 20
SPAWN_X = 400
SPAWN_Y = 400


def _now():
    """Return the current simulation tick."""
    return globalvar.get_value("time", 0) or 0


class Rider:
    """A delivery rider that moves on the street grid and serves orders.

    Attributes:
        rider_id: Unique integer identifier.
        x, y: Current integer coordinates.
        speed: Movement budget in units per tick.
        state: 0 idle, 1 picking up, 2 delivering.
        orders: All orders ever assigned (completed ones kept as history).
        special_case: True when the rider is mid-block or directly above or
            below its current target.
        log: List of event dicts with keys "event", "order_id", "time",
            "x", "y", "state" and "rider_id".
        path: Remaining waypoints for the current leg.
        target: Current destination intersection.
        distance_travelled: Total distance moved so far.
    """

    def __init__(self, rider_id, x=SPAWN_X, y=SPAWN_Y, speed=DEFAULT_SPEED):
        """Create a rider.

        Args:
            rider_id: Unique rider identifier.
            x: Starting X coordinate (default 400).
            y: Starting Y coordinate (default 400).
            speed: Units moved per tick (default 20).
        """
        self.rider_id = rider_id
        self.x = x
        self.y = y
        self.speed = speed
        self.state = IDLE
        self.orders = []
        self.special_case = False
        self.log = []
        self.path = []
        self.target = None
        self.distance_travelled = 0
        self._planner = PathPlanner()
        self._record("spawn", None)
        logger.info("Rider #%s spawned at (%s, %s)", rider_id, x, y)

    @property
    def position(self):
        """Return the current position as an ``(x, y)`` tuple."""
        return (self.x, self.y)

    def current_order(self):
        """Return the order currently being served, or None."""
        for order in self.orders:
            if order.status != "completed":
                return order
        return None

    def active_order_count(self):
        """Return the number of assigned orders that are not completed."""
        return sum(1 for order in self.orders if order.status != "completed")

    def accept_order(self, order):
        """Handle a newly assigned order (called by ``Order.assign_to``).

        Logs the acceptance. If the rider is idle the pickup leg starts
        immediately; otherwise the order is queued behind current work.

        Args:
            order: The order that has just been appended to ``self.orders``.
        """
        self._record("accepted_order", order.id)
        if self.state == IDLE and self.current_order() is order:
            self._begin_pickup(order)

    def move(self):
        """Advance the rider by one tick.

        Spends up to ``speed`` units of movement along the planned route and
        processes any arrival events (restaurant pickup, customer delivery)
        that result from this movement.
        """
        order = self.current_order()
        if order is None:
            if self.state != IDLE:
                self._go_idle()
            return
        if self.state == IDLE:
            self._begin_pickup(order)

        self.distance_travelled += self._advance()

        for _ in range(3):
            if self.path:
                break
            order = self.current_order()
            if order is None:
                self._go_idle()
                break
            if self.state == PICKING_UP and self.position == order.restaurant:
                self._arrive_at_merchant(order)
            elif self.state == DELIVERING and self.position == order.customer:
                self._deliver(order)
            else:
                break

    def route_to_order(self, order):
        """Return the planned route from the rider's position through ``order``.

        The route includes pickup and delivery legs of all unfinished orders
        queued up to and including ``order``. Used for route previews.

        Args:
            order: The order whose route should be previewed.

        Returns:
            List of ``(x, y)`` points starting at the rider's position.
        """
        points = [self.position]
        cur = self.position
        stops = []
        current = self.current_order()
        for queued in self.orders:
            if queued.status == "completed":
                continue
            if queued is current and self.state == DELIVERING:
                stops.append(queued.customer)
            else:
                stops.append(queued.restaurant)
                stops.append(queued.customer)
            if queued is order:
                break
        for stop in stops:
            if stop == cur:
                continue
            points.extend(self._planner.plan(cur, stop))
            cur = stop
        return points

    def remaining_distance(self):
        """Return the length of the remaining route for the current leg."""
        return route_length([self.position] + self.path)

    def estimated_ticks(self):
        """Return the estimated number of ticks to finish the current leg."""
        if self.speed <= 0:
            return math.inf
        return math.ceil(self.remaining_distance() / self.speed)

    def _record(self, event, order_id):
        """Append an event entry to the rider log."""
        self.log.append({
            "event": event,
            "order_id": order_id,
            "time": _now(),
            "x": self.x,
            "y": self.y,
            "state": self.state,
            "rider_id": self.rider_id,
        })

    def _set_route(self, goal):
        """Plan a route to ``goal`` and update the special-case flag."""
        self.target = goal
        self.path = self._planner.plan(self.position, goal)
        self.special_case = (self.x == goal[0]) or not is_intersection(self.x, self.y)

    def _begin_pickup(self, order):
        """Switch to the picking-up state and route to the restaurant."""
        self.state = PICKING_UP
        order.status = "picking_up"
        self._set_route(order.restaurant)
        logger.info("Rider #%s heading to restaurant %s for order #%s",
                    self.rider_id, order.restaurant, order.id)

    def _arrive_at_merchant(self, order):
        """Handle arrival at the restaurant and start the delivery leg."""
        self.state = DELIVERING
        order.status = "delivering"
        order.pickup_time = _now()
        self._record("arrived_at_merchant", order.id)
        self._set_route(order.customer)

    def _deliver(self, order):
        """Handle delivery to the customer and move on to the next order."""
        order.complete(_now())
        self._record("delivered_to_customer", order.id)
        logger.info("Rider #%s delivered order #%s", self.rider_id, order.id)
        nxt = self.current_order()
        if nxt is None:
            self._go_idle()
        else:
            self.state = PICKING_UP
            nxt.status = "picking_up"
            self._set_route(nxt.restaurant)

    def _go_idle(self):
        """Release the rider back to the idle pool."""
        self.state = IDLE
        self.path = []
        self.target = None
        self.special_case = False

    def _advance(self):
        """Move along the planned waypoints using up to ``speed`` units.

        Returns:
            The number of units actually moved.
        """
        remaining = self.speed
        moved = 0
        while remaining > 0 and self.path:
            wx, wy = self.path[0]
            dx = wx - self.x
            dy = wy - self.y
            dist = abs(dx) + abs(dy)
            if dist <= remaining:
                self.x, self.y = wx, wy
                remaining -= dist
                moved += dist
                self.path.pop(0)
            else:
                if dx != 0:
                    self.x += remaining if dx > 0 else -remaining
                else:
                    self.y += remaining if dy > 0 else -remaining
                moved += remaining
                remaining = 0
        return moved
