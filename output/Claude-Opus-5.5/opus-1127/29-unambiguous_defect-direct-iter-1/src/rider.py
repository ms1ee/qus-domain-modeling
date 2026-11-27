"""Rider model: movement, state machine and order handling."""

import logging

import globalvar
from config import DEFAULT_CONFIG
from path_planner import PathPlanner, to_grid_point

logger = logging.getLogger(__name__)

IDLE = 0
PICKING_UP = 1
DELIVERING = 2
STATE_NAMES = {IDLE: "idle", PICKING_UP: "picking up", DELIVERING: "delivering"}

SPAWN_POINTS = [
    (400, 400), (0, 0), (800, 800), (0, 800), (800, 0), (400, 0),
    (0, 400), (800, 400), (400, 800), (200, 200), (600, 600),
    (200, 600), (600, 200),
]


def _order_points(order):
    """Return ``(res_pos, cus_pos)`` of an Order or a 4-element sequence."""
    if hasattr(order, "res_pos") and hasattr(order, "cus_pos"):
        return tuple(order.res_pos), tuple(order.cus_pos)
    vals = list(order)
    return (to_grid_point(vals[0:2]), to_grid_point(vals[2:4]))


def _set_attr(order, name, value):
    """Set an attribute on an order object if possible."""
    try:
        setattr(order, name, value)
    except AttributeError:
        pass


class Rider:
    """A delivery rider.

    Attributes:
        rider_id: unique id.
        x, y: current position.
        speed: units moved per tick.
        state: 0 idle, 1 picking up, 2 delivering.
        orders: assigned orders (first one is the active one).
        special_case: True while handling a special path case.
        log: list of event dicts (keys include "event" and "order_id").
    """

    def __init__(self, rider_id, x=None, y=None, speed=None):
        self.rider_id = rider_id
        sx, sy = SPAWN_POINTS[int(rider_id) % len(SPAWN_POINTS)]
        self.x = sx if x is None else int(x)
        self.y = sy if y is None else int(y)
        if speed is None:
            cfg = globalvar.get_value("config") or DEFAULT_CONFIG
            speed = cfg.get("rider_speed", DEFAULT_CONFIG["rider_speed"])
        self.speed = max(1, int(speed))
        self.state = IDLE
        self.orders = []
        self.special_case = False
        self.log = []
        self.path = []
        self.distance_travelled = 0
        self.completed_count = 0
        self._planner = PathPlanner()
        self._record("spawn", None)

    # ------------------------------------------------------------------
    def _record(self, event, order):
        """Append a log entry for a status change."""
        order_id = None
        if order is not None:
            order_id = getattr(order, "id", None)
        self.log.append({
            "event": event,
            "order_id": order_id,
            "time": globalvar.get_value("time", 0) or 0,
            "x": self.x,
            "y": self.y,
            "state": self.state,
        })
        logger.debug("Rider %s: %s (order %s) at (%s, %s)",
                     self.rider_id, event, order_id, self.x, self.y)

    def _plan_to(self, target):
        """Plan a path from the current position to ``target``."""
        self.path = self._planner.plan((self.x, self.y), target)
        self.special_case = self._planner.last_special

    def _accept(self, order):
        """Idle -> picking up: accept the first order in the queue."""
        res, _ = _order_points(order)
        self.state = PICKING_UP
        now = globalvar.get_value("time", 0) or 0
        _set_attr(order, "status", "picking_up")
        _set_attr(order, "accepted_time", now)
        if getattr(order, "rider_id", "x") is None:
            _set_attr(order, "rider_id", self.rider_id)
        self._plan_to(res)
        self._record("accepted_order", order)

    def _on_arrival(self):
        """Handle reaching the end of the current path."""
        if not self.orders:
            return
        order = self.orders[0]
        res, cus = _order_points(order)
        now = globalvar.get_value("time", 0) or 0
        if self.state == PICKING_UP:
            if (self.x, self.y) != res:
                self._plan_to(res)
                return
            self.state = DELIVERING
            _set_attr(order, "status", "delivering")
            _set_attr(order, "picked_time", now)
            self._record("arrived_at_merchant", order)
            self._plan_to(cus)
        elif self.state == DELIVERING:
            if (self.x, self.y) != cus:
                self._plan_to(cus)
                return
            self._complete(order, now)

    def _complete(self, order, now):
        """Delivering -> idle: finish the active order."""
        _set_attr(order, "status", "completed")
        _set_attr(order, "completed_time", now)
        created = getattr(order, "created_time", None)
        if created is not None:
            _set_attr(order, "time_taken", now - created)
        self.orders.pop(0)
        self.state = IDLE
        self.special_case = False
        self.path = []
        self.completed_count += 1
        cfg = globalvar.get_value("config") or DEFAULT_CONFIG
        fee = cfg.get("delivery_fee", 0)
        if globalvar.get_value("funds") is not None and fee:
            globalvar.set_value("funds", globalvar.get_value("funds") + fee)
        self._record("delivered_to_customer", order)

    def _step(self):
        """Advance along the path by at most ``speed`` units."""
        budget = self.speed
        while budget > 0 and self.path:
            tx, ty = self.path[0]
            dx = tx - self.x
            dy = ty - self.y
            dist = abs(dx) + abs(dy)
            if dist <= budget:
                self.x, self.y = tx, ty
                budget -= dist
                self.distance_travelled += dist
                self.path.pop(0)
            else:
                step = budget
                if dx != 0:
                    mv = min(step, abs(dx))
                    self.x += mv if dx > 0 else -mv
                    step -= mv
                if step > 0 and dy != 0:
                    mv = min(step, abs(dy))
                    self.y += mv if dy > 0 else -mv
                self.distance_travelled += budget
                budget = 0

    def move(self):
        """Advance the rider by one tick, performing state transitions."""
        if self.state == IDLE:
            if not self.orders:
                return
            self._accept(self.orders[0])
        if not self.orders:
            # Inconsistent state: busy without orders -> recover.
            self.state = IDLE
            self.path = []
            self.special_case = False
            return
        self._step()
        if not self.path:
            self._on_arrival()

    # ------------------------------------------------------------------
    @property
    def state_name(self):
        """Human readable state."""
        return STATE_NAMES.get(self.state, "unknown")

    def remaining_path(self):
        """Current position followed by the remaining waypoints."""
        return [(self.x, self.y)] + list(self.path)

    def to_dict(self):
        """Serializable representation of the rider."""
        return {
            "rider_id": self.rider_id,
            "x": self.x,
            "y": self.y,
            "speed": self.speed,
            "state": self.state,
            "orders": [getattr(o, "id", None) for o in self.orders],
            "special_case": self.special_case,
            "distance_travelled": self.distance_travelled,
            "completed_count": self.completed_count,
            "log": list(self.log),
        }

    def __repr__(self):
        return "Rider(id=%s, pos=(%s, %s), state=%s, orders=%d)" % (
            self.rider_id, self.x, self.y, self.state, len(self.orders))
