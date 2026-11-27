"""Rider model: state transitions, movement along streets and event logging."""

import globalvar
from path_planner import PathPlanner, GRID_SIZE

IDLE = 0
PICKING_UP = 1
DELIVERING = 2

STATE_NAMES = {
    IDLE: "idle",
    PICKING_UP: "picking up",
    DELIVERING: "delivering",
}

DEFAULT_SPEED = 60

_PLANNER = PathPlanner()


def spawn_position(rider_id):
    """Return a deterministic starting street intersection for a rider.

    Args:
        rider_id: Unique rider identifier.

    Returns:
        Tuple ``(x, y)`` of an intersection on the map.
    """
    nodes_per_axis = GRID_SIZE + 1
    index = (rider_id * 7) % (nodes_per_axis * nodes_per_axis)
    return (index % nodes_per_axis) * 100, (index // nodes_per_axis) * 100


class Rider:
    """A delivery rider that moves along streets and serves orders.

    Attributes:
        rider_id (int): Unique identifier.
        x (int): Current X coordinate.
        y (int): Current Y coordinate.
        speed (int): Distance units travelled per tick.
        state (int): 0 = idle, 1 = picking up, 2 = delivering.
        orders (list): Assigned orders; the first entry is the active order.
        special_case (bool): True while the rider is between intersections.
        log (list[dict]): Status change records with keys ``event``,
            ``order_id``, ``rider_id``, ``time``, ``x`` and ``y``.
    """

    def __init__(self, rider_id, speed=DEFAULT_SPEED):
        """Create a rider at a spawn point on a street.

        Args:
            rider_id: Unique rider identifier.
            speed: Movement speed in units per tick (positive integer).

        Raises:
            ValueError: If the speed is not a positive integer.
        """
        if isinstance(speed, bool) or not isinstance(speed, int) or speed <= 0:
            raise ValueError("rider speed must be a positive integer")
        self.rider_id = rider_id
        self.x, self.y = spawn_position(rider_id)
        self.speed = speed
        self.state = IDLE
        self.orders = []
        self.special_case = False
        self.log = []
        self._waypoints = []
        self._target = None
        self._log("spawn", None)

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------
    @property
    def position(self):
        """Return the current ``(x, y)`` position."""
        return self.x, self.y

    @property
    def state_name(self):
        """Return a human-readable name for the current state."""
        return STATE_NAMES.get(self.state, "unknown")

    @staticmethod
    def _now():
        """Return the current simulated time from the global store."""
        return globalvar.get_value("simulated_time", 0)

    def _log(self, event, order):
        """Append a status change record to :attr:`log`."""
        self.log.append({
            "event": event,
            "order_id": order.id if order is not None else None,
            "rider_id": self.rider_id,
            "time": self._now(),
            "x": self.x,
            "y": self.y,
        })

    def _set_target(self, target):
        """Plan a route from the current position to ``target``."""
        route = _PLANNER.plan((self.x, self.y), target, self.speed)
        self._waypoints = route.waypoints[1:]

    def reset_navigation(self):
        """Clear any planned route, used for error recovery."""
        self._waypoints = []
        self._target = None

    def summary(self):
        """Return a dictionary describing the rider's current status."""
        return {
            "rider_id": self.rider_id,
            "x": self.x,
            "y": self.y,
            "speed": self.speed,
            "state": self.state,
            "state_name": self.state_name,
            "special_case": self.special_case,
            "orders": [order.id for order in self.orders],
        }

    # ------------------------------------------------------------------
    # Movement and state transitions
    # ------------------------------------------------------------------
    def _advance(self):
        """Move up to ``speed`` units along the planned waypoints."""
        budget = self.speed
        while budget > 0 and self._waypoints:
            tx, ty = self._waypoints[0]
            dx = tx - self.x
            dy = ty - self.y
            distance = abs(dx) + abs(dy)
            if distance <= budget:
                self.x, self.y = tx, ty
                budget -= distance
                self._waypoints.pop(0)
            else:
                if dx != 0:
                    self.x += budget if dx > 0 else -budget
                else:
                    self.y += budget if dy > 0 else -budget
                budget = 0

    def _begin_pickup(self):
        """Transition from idle (or finished order) to picking up."""
        order = self.orders[0]
        self.state = PICKING_UP
        order.status = "picking_up"
        self._log("accepted_order", order)
        self._set_target(order.restaurant_pos)

    def _handle_arrival(self):
        """Process reaching the current target and return completed orders."""
        if not self.orders:
            self.state = IDLE
            self.reset_navigation()
            return []

        order = self.orders[0]
        if self.state == PICKING_UP:
            self._log("arrived_at_merchant", order)
            self.state = DELIVERING
            order.status = "delivering"
            self._set_target(order.customer_pos)
            return []

        # DELIVERING: the customer has been reached.
        order.complete(self._now())
        self._log("delivered_to_customer", order)
        self.orders.pop(0)
        self.reset_navigation()
        if self.orders:
            self._begin_pickup()
        else:
            self.state = IDLE
        return [order]

    def move(self):
        """Advance the rider by one tick.

        Idle riders with assigned orders start picking up. Riders in motion
        advance along their route; reaching the restaurant switches them to
        delivering, and reaching the customer completes the order.

        Returns:
            List of orders completed during this tick.
        """
        completed = []
        if self.state == IDLE:
            if not self.orders:
                return completed
            self._begin_pickup()

        if self.state not in (PICKING_UP, DELIVERING):
            return completed

        self._advance()
        if not self._waypoints:
            completed = self._handle_arrival()
        self.special_case = not _PLANNER.is_intersection(self.x, self.y)
        return completed
