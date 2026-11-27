"""Rider model: movement, state machine and order handling."""

import logging

import globalvar
from path_planner import PathPlanner, MAP_SIZE

logger = logging.getLogger(__name__)

STATE_IDLE = 0
STATE_PICKING_UP = 1
STATE_DELIVERING = 2

STATE_NAMES = {
    STATE_IDLE: "idle",
    STATE_PICKING_UP: "picking up",
    STATE_DELIVERING: "delivering",
}

DEFAULT_SPEED = 20
DEFAULT_START = (400, 400)


def _pos(pos):
    """Return a position as an ``(int, int)`` tuple."""
    return int(pos[0]), int(pos[1])


def _now():
    """Current simulated time."""
    return globalvar.get_value("current_time", 0) or 0


class Rider:
    """A delivery rider.

    Orders are assigned by appending them to :attr:`orders`.  Calling
    :meth:`move` advances the rider by one tick, performing state
    transitions and logging events.
    """

    def __init__(self, rider_id, x=None, y=None, speed=None):
        start = globalvar.get_value("rider_start", DEFAULT_START) or DEFAULT_START
        self.rider_id = rider_id
        self.x = int(start[0]) if x is None else int(x)
        self.y = int(start[1]) if y is None else int(y)
        if speed is None:
            speed = globalvar.get_value("rider_speed", DEFAULT_SPEED) or DEFAULT_SPEED
        self.speed = int(speed)
        self.state = STATE_IDLE
        self.orders = []
        self.special_case = False
        self.current_order = None
        self.path = []
        self.total_distance = 0
        self.log = []
        self._record("spawn", None)

    # ------------------------------------------------------------------ #
    # Helpers
    # ------------------------------------------------------------------ #
    def _record(self, event, order_id):
        """Append an event entry to the rider log."""
        entry = {
            "event": event,
            "order_id": order_id,
            "time": _now(),
            "x": self.x,
            "y": self.y,
            "state": self.state,
        }
        self.log.append(entry)
        logger.debug("Rider %s: %s", self.rider_id, entry)

    @property
    def state_name(self):
        """Human readable state."""
        return STATE_NAMES.get(self.state, str(self.state))

    @property
    def position(self):
        """Current position tuple."""
        return self.x, self.y

    def active_orders(self):
        """Orders that are not yet completed."""
        return [o for o in self.orders
                if getattr(o, "status", None) != "completed"]

    def active_order_count(self):
        """Number of not yet completed orders."""
        return len(self.active_orders())

    def is_idle(self):
        """True if the rider has nothing to do."""
        return self.state == STATE_IDLE and not self.active_orders()

    def _next_pending_order(self):
        for order in self.orders:
            if order is self.current_order:
                continue
            if getattr(order, "status", None) != "completed":
                return order
        return None

    def _current_target(self):
        if self.current_order is None:
            return None
        if self.state == STATE_DELIVERING:
            return _pos(self.current_order.cus_pos)
        return _pos(self.current_order.res_pos)

    def _plan(self, target):
        self.special_case = PathPlanner.is_special_case(self.position, target)
        self.path = PathPlanner.plan_path(self.position, target)
        if not self.path and self.position != target:
            self.path = [target]

    def _accept(self, order):
        self.current_order = order
        if getattr(order, "rider_id", None) is None:
            try:
                order.rider_id = self.rider_id
            except AttributeError:
                pass
        order.status = "picking_up"
        if hasattr(order, "accepted_time"):
            order.accepted_time = _now()
        self.state = STATE_PICKING_UP
        self._record("accepted_order", order.id)
        self._plan(_pos(order.res_pos))

    def _advance(self, budget):
        """Move along the planned path using up to ``budget`` units."""
        while budget > 0 and self.path:
            wx, wy = self.path[0]
            dx = wx - self.x
            dy = wy - self.y
            dist = abs(dx) + abs(dy)
            if dist <= budget:
                self.x, self.y = wx, wy
                budget -= dist
                self.total_distance += dist
                self.path.pop(0)
                continue
            # Partial move, x axis first then y axis.
            step_x = min(abs(dx), budget)
            self.x += step_x if dx > 0 else -step_x
            budget -= step_x
            self.total_distance += step_x
            if budget > 0:
                step_y = min(abs(dy), budget)
                self.y += step_y if dy > 0 else -step_y
                budget -= step_y
                self.total_distance += step_y
        self.x = max(0, min(MAP_SIZE, self.x))
        self.y = max(0, min(MAP_SIZE, self.y))
        return budget

    def _handle_arrival(self):
        """Handle reaching the current target.

        Returns True if the tick should end (an order was delivered).
        """
        order = self.current_order
        if self.state == STATE_PICKING_UP:
            self.state = STATE_DELIVERING
            order.status = "delivering"
            if hasattr(order, "pickup_time"):
                order.pickup_time = _now()
            self._record("arrived_at_merchant", order.id)
            self.path = []
            return False
        # Delivering -> delivered.
        order.status = "completed"
        if hasattr(order, "completed_time"):
            order.completed_time = _now()
        self._record("delivered_to_customer", order.id)
        self.current_order = None
        self.path = []
        self.special_case = False
        nxt = self._next_pending_order()
        if nxt is not None:
            self._accept(nxt)
        else:
            self.state = STATE_IDLE
        return True

    # ------------------------------------------------------------------ #
    # Public API
    # ------------------------------------------------------------------ #
    def move(self):
        """Advance the rider by one tick."""
        if self.current_order is not None and (
                self.current_order not in self.orders
                or self.current_order.status == "completed"):
            self.current_order = None
            self.path = []
        if self.current_order is None:
            nxt = self._next_pending_order()
            if nxt is None:
                self.state = STATE_IDLE
                self.path = []
                return
            self._accept(nxt)

        budget = self.speed
        guard = 0
        while self.current_order is not None and guard < 32:
            guard += 1
            target = self._current_target()
            if self.position != target and not self.path:
                self._plan(target)
            budget = self._advance(budget)
            if self.position == target:
                if self._handle_arrival():
                    break
                continue
            if budget <= 0:
                break

    def planned_route(self):
        """Full list of waypoints for the remaining work, starting with the
        current position (current target then customer, then queued orders).
        """
        points = [self.position]
        if self.current_order is None and not self.active_orders():
            return points
        stops = []
        if self.current_order is not None:
            if self.state == STATE_PICKING_UP:
                stops.append(_pos(self.current_order.res_pos))
            stops.append(_pos(self.current_order.cus_pos))
        for order in self.active_orders():
            if order is self.current_order:
                continue
            stops.append(_pos(order.res_pos))
            stops.append(_pos(order.cus_pos))
        points.extend(PathPlanner.plan_multi(self.position, stops))
        return points

    def estimated_ticks(self):
        """Estimated ticks to finish all remaining work."""
        route = self.planned_route()
        length = PathPlanner.path_length(route[0], route[1:])
        if self.speed <= 0:
            return None
        return -(-length // self.speed)

    def to_dict(self):
        """Serialise to a JSON compatible dict."""
        return {
            "rider_id": self.rider_id,
            "x": self.x,
            "y": self.y,
            "speed": self.speed,
            "state": self.state,
            "orders": [o.id for o in self.orders],
            "current_order": self.current_order.id if self.current_order else None,
            "special_case": self.special_case,
            "total_distance": self.total_distance,
            "log": list(self.log),
        }

    def __repr__(self):
        return ("Rider(id={}, pos=({}, {}), state={}, orders={})"
                .format(self.rider_id, self.x, self.y, self.state_name,
                        len(self.orders)))
