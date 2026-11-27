"""Rider model: state management, order queue, movement and status logging."""

import logging

import globalvar
from config import CONFIG
from path_planner import PathPlanner

logger = logging.getLogger("dispatch")

IDLE = 0
PICKING_UP = 1
DELIVERING = 2

STATE_NAMES = {
    IDLE: "idle",
    PICKING_UP: "picking up",
    DELIVERING: "delivering",
}

SPAWN_POSITION = (0, 0)


class Rider:
    """A delivery rider that moves across the grid and serves orders.

    Attributes:
        rider_id: Unique integer identifier.
        x, y: Current position in map units.
        speed: Movement units per tick.
        state: 0 = idle, 1 = picking up, 2 = delivering.
        orders: Queue of assigned orders; ``orders[0]`` is the active order.
        special_case: True when the rider moves straight to a target that is
            directly above/below it (same x coordinate).
        waypoints: Remaining route points for the current leg.
        log: List of dict entries with keys "event" and "order_id".
        history: Detailed status-change records (time, position, state).
        distance_travelled: Total distance moved over the rider's lifetime.
    """

    def __init__(self, rider_id):
        """Create a rider at the spawn position in the idle state.

        Args:
            rider_id: Unique identifier assigned by the system.
        """
        self.rider_id = int(rider_id)
        self.x, self.y = SPAWN_POSITION
        self.speed = int(CONFIG["rider_speed"])
        self.state = IDLE
        self.orders = []
        self.special_case = False
        self.waypoints = []
        self.log = []
        self.history = []
        self.distance_travelled = 0
        self._planner = PathPlanner()
        self._record("spawn", None)

    # ------------------------------------------------------------------ helpers
    @staticmethod
    def _now():
        """Return the current simulated tick."""
        return int(globalvar.get_value("tick", 0) or 0)

    def _record(self, event, order_id):
        """Append an event to both the log and the detailed history."""
        self.log.append({"event": event, "order_id": order_id})
        self.history.append({
            "time": self._now(),
            "event": event,
            "order_id": order_id,
            "x": self.x,
            "y": self.y,
            "state": self.state,
        })
        logger.debug("Rider %s event %s order %s", self.rider_id, event, order_id)

    @property
    def current_order(self):
        """Return the order currently being served, or None."""
        return self.orders[0] if self.orders else None

    def position(self):
        """Return the current (x, y) position."""
        return (self.x, self.y)

    def _plan_leg(self, target):
        """Plan the route from the current position to ``target``."""
        tx, ty = target
        route = self._planner.plan((self.x, self.y), (tx, ty), self.speed)
        self.waypoints = list(route.waypoints)
        self.special_case = self.x == tx and self.y != ty

    def _advance(self, budget):
        """Move along the planned waypoints using at most ``budget`` units.

        Returns:
            The number of units actually moved.
        """
        moved = 0
        while budget > 0 and self.waypoints:
            tx, ty = self.waypoints[0]
            dx, dy = tx - self.x, ty - self.y
            distance = abs(dx) + abs(dy)
            if distance <= budget:
                self.x, self.y = tx, ty
                self.waypoints.pop(0)
                budget -= distance
                moved += distance
            else:
                if dx != 0:
                    self.x += budget if dx > 0 else -budget
                else:
                    self.y += budget if dy > 0 else -budget
                moved += budget
                budget = 0
        self.distance_travelled += moved
        return moved

    def _leg_finished(self, now):
        """Handle arrival at the end of the current leg (state transition)."""
        if self.state == PICKING_UP:
            order = self.current_order
            if order is None:
                self.state = IDLE
                return
            self._record("arrived_at_merchant", order.id)
            self.state = DELIVERING
            order.status = "delivering"
            self._plan_leg(order.customer_center)
            if not self.waypoints:
                self._leg_finished(now)
        elif self.state == DELIVERING:
            if not self.orders:
                self.state = IDLE
                return
            order = self.orders.pop(0)
            order.complete(now)
            self._record("delivered_to_customer", order.id)
            self.state = IDLE
            self.waypoints = []
            self.special_case = False

    # --------------------------------------------------------------- public API
    def move(self):
        """Advance the rider by one tick.

        State transitions happen here:
            * Idle -> Picking up when an order is queued (logs "accepted_order").
            * Picking up -> Delivering on reaching the restaurant
              (logs "arrived_at_merchant").
            * Delivering -> Idle on reaching the customer
              (logs "delivered_to_customer").

        Returns:
            Distance moved during this tick.
        """
        now = self._now()
        if self.state == IDLE:
            order = self.current_order
            if order is None:
                return 0
            self.state = PICKING_UP
            order.status = "picking_up"
            self._record("accepted_order", order.id)
            self._plan_leg(order.restaurant_center)

        moved = self._advance(self.speed)
        if self.orders and moved:
            self.orders[0].distance += moved

        if not self.waypoints and self.state in (PICKING_UP, DELIVERING):
            self._leg_finished(now)
        return moved

    def to_dict(self):
        """Return a JSON-serialisable snapshot of the rider."""
        return {
            "rider_id": self.rider_id,
            "x": self.x,
            "y": self.y,
            "speed": self.speed,
            "state": self.state,
            "state_name": STATE_NAMES.get(self.state, "unknown"),
            "orders": [order.id for order in self.orders],
            "special_case": self.special_case,
            "distance_travelled": self.distance_travelled,
            "log": list(self.log),
        }
