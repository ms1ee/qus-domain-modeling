"""Rider entity: state machine, grid movement and event logging.

Rider states:
    0 (IDLE)        - available for new orders.
    1 (PICKING_UP)  - driving to the restaurant of the current order.
    2 (DELIVERING)  - driving to the customer of the current order.

Logged events (``Rider.log``): ``spawn``, ``accepted_order``,
``arrived_at_merchant``, ``delivered_to_customer``.
"""

import logging

import globalvar
from path_planner import MAP_SIZE, PathPlanner, cell_center, cell_of, straight_line_case

logger = logging.getLogger(__name__)

IDLE = 0
PICKING_UP = 1
DELIVERING = 2
STATE_NAMES = {IDLE: "idle", PICKING_UP: "picking up", DELIVERING: "delivering"}

DEFAULT_SPEED = 50
SPAWN_CELL = (0, 0)


def _config_value(key, default):
    """Read a parameter from the global configuration."""
    config = globalvar.get_value("config") or {}
    return config.get(key, default)


def _current_tick():
    """Return the current simulated tick."""
    return int(globalvar.get_value("current_tick") or 0)


def _sign(value):
    """Return -1, 0 or 1 according to the sign of ``value``."""
    return (value > 0) - (value < 0)


class Rider:
    """A delivery rider moving on the grid.

    Attributes:
        rider_id: Unique integer identifier.
        x: Current horizontal position (0-800).
        y: Current vertical position (0-800).
        speed: Movement speed in units per tick.
        state: Current state enum (0 idle, 1 picking up, 2 delivering).
        orders: Assigned orders; the first element is the active order.
        special_case: True while moving straight to an aligned target.
        path: Remaining waypoints (cell centers) toward the target.
        target: Current destination point ``(x, y)`` or None.
        log: Chronological list of event dictionaries.
    """

    _planner = PathPlanner()

    def __init__(self, rider_id):
        """Create a rider at the spawn point, idle, with no orders.

        Args:
            rider_id: Unique identifier for the rider.
        """
        self.rider_id = int(rider_id)
        self.x, self.y = cell_center(*SPAWN_CELL)
        speed = int(_config_value("rider_speed", DEFAULT_SPEED))
        self.speed = speed if speed > 0 else DEFAULT_SPEED
        self.state = IDLE
        self.orders = []
        self.special_case = False
        self.path = []
        self.target = None
        self.log = []
        self._record("spawn", None)

    @property
    def position(self):
        """Return the current position as ``(x, y)``."""
        return self.x, self.y

    @property
    def state_name(self):
        """Return a human readable name of the current state."""
        return STATE_NAMES.get(self.state, "unknown")

    def move(self):
        """Advance the rider by one tick.

        Handles idle → picking up activation, arrival at the restaurant
        (picking up → delivering) and delivery completion
        (delivering → idle, or picking up the next queued order).

        Returns:
            True if an order was delivered during this tick, else False.
        """
        if not self.orders:
            self._become_idle()
            return False

        if self.state == IDLE:
            order = self.orders[0]
            self.state = PICKING_UP
            order.status = "picking_up"
            self._record("accepted_order", order.id)
            self._set_target(order.restaurant_pos)

        self._advance()
        if self._at_target():
            return self._handle_arrival()
        return False

    def recover(self):
        """Restore a consistent state after an unexpected error."""
        logger.warning("Recovering rider %s", self.rider_id)
        self.x = min(max(int(self.x), 0), MAP_SIZE)
        self.y = min(max(int(self.y), 0), MAP_SIZE)
        self.path = []
        self.special_case = False
        if not self.orders:
            self.state = IDLE
            self.target = None
            return
        order = self.orders[0]
        if self.state == DELIVERING:
            self.target = order.customer_pos
        else:
            self.state = PICKING_UP
            order.status = "picking_up"
            self.target = order.restaurant_pos

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
            "log": list(self.log),
        }

    def _become_idle(self):
        """Reset the rider to the idle state."""
        if self.state != IDLE:
            self.state = IDLE
        self.path = []
        self.target = None
        self.special_case = False

    def _set_target(self, point):
        """Set a new destination and clear the planned path."""
        self.target = point
        self.path = []
        self.special_case = False

    def _at_target(self):
        """Return True if the rider stands on its current target."""
        return self.target is not None and (self.x, self.y) == self.target

    def _other_rider_cells(self):
        """Return the set of cells occupied by other riders."""
        riders = globalvar.get_value("riders") or []
        return {cell_of(r.x, r.y) for r in riders if r is not self}

    def _plan_to(self, target):
        """Compute the waypoint path from the current cell to ``target``."""
        start = cell_of(self.x, self.y)
        goal = cell_of(target[0], target[1])
        route = self._planner.plan_route(start, goal, self._other_rider_cells())
        self.path = [cell_center(gx, gy) for gx, gy in route.waypoints[1:]]
        self.special_case = straight_line_case(start, goal)

    def _advance(self):
        """Move up to ``speed`` units along the planned path."""
        if self.target is None or self._at_target():
            return
        if not self.path:
            self._plan_to(self.target)
        budget = self.speed
        while budget > 0 and self.path:
            nx, ny = self.path[0]
            dx = nx - self.x
            dy = ny - self.y
            distance = abs(dx) + abs(dy)
            if distance <= budget:
                self.x, self.y = nx, ny
                self.path.pop(0)
                budget -= distance
            else:
                if dx != 0:
                    self.x += _sign(dx) * budget
                else:
                    self.y += _sign(dy) * budget
                budget = 0

    def _handle_arrival(self):
        """Process reaching the current target.

        Returns:
            True if the rider completed a delivery.
        """
        order = self.orders[0]
        if self.state == PICKING_UP:
            self._record("arrived_at_merchant", order.id)
            self.state = DELIVERING
            order.status = "delivering"
            self._set_target(order.customer_pos)
            return False

        if self.state == DELIVERING:
            income = order.complete(_current_tick())
            self._adjust_funds(income)
            self._record("delivered_to_customer", order.id)
            self.orders.pop(0)
            self.path = []
            self.target = None
            self.special_case = False
            if self.orders:
                next_order = self.orders[0]
                self.state = PICKING_UP
                next_order.status = "picking_up"
                self._record("accepted_order", next_order.id)
                self._set_target(next_order.restaurant_pos)
            else:
                self.state = IDLE
            return True
        return False

    def _adjust_funds(self, delta):
        """Add ``delta`` to the system funds."""
        current = int(globalvar.get_value("funds") or 0)
        globalvar.set_value("funds", current + int(delta))

    def _record(self, event, order_id):
        """Append an event entry to the rider log."""
        entry = {
            "time": _current_tick(),
            "rider_id": self.rider_id,
            "event": event,
            "x": self.x,
            "y": self.y,
            "order_id": order_id,
        }
        self.log.append(entry)
        logger.debug("Rider %s event %s order=%s", self.rider_id, event, order_id)
