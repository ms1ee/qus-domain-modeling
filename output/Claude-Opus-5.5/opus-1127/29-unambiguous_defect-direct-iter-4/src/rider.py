"""Rider model: movement, state transitions and orders."""

import logging

import globalvar
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

DEFAULT_SPEED = 50

# Starting locations on roads (street intersections).
SPAWN_POINTS = [
    (400, 400), (200, 200), (600, 600), (200, 600), (600, 200),
    (400, 0), (0, 400), (800, 400), (400, 800), (0, 0),
]


def _now():
    """Current simulated time (tick)."""
    t = globalvar.get_value("time", 0)
    return t if isinstance(t, int) else 0


def _config():
    cfg = globalvar.get_value("config")
    return cfg if isinstance(cfg, dict) else {}


class Rider:
    """A delivery rider.

    Attributes:
        rider_id: unique identifier.
        x, y: current position (integers 0..800, starts on a road).
        speed: units travelled per tick.
        state: 0 idle, 1 picking up, 2 delivering.
        orders: list of assigned orders (first one is processed first).
        special_case: True when the current route needs a detour.
        log: list of dict entries with keys including "event" and "order_id".
    """

    def __init__(self, rider_id, x=None, y=None, speed=None):
        self.rider_id = int(rider_id)
        cfg = _config()
        if x is None or y is None:
            x, y = SPAWN_POINTS[self.rider_id % len(SPAWN_POINTS)]
        self.x, self.y = PathPlanner.snap_to_road(x, y)
        if speed is None:
            speed = cfg.get("rider_speed", DEFAULT_SPEED)
        try:
            speed = int(speed)
        except (TypeError, ValueError):
            speed = DEFAULT_SPEED
        self.speed = speed if speed > 0 else DEFAULT_SPEED
        self.state = STATE_IDLE
        self.orders = []
        self.special_case = False
        self.current_order = None
        self.path = []
        self.distance_travelled = 0
        self.delivered_count = 0
        self.log = []
        self._record("spawn", None)

    # ------------------------------------------------------------------ helpers
    @property
    def state_name(self):
        """Human readable state."""
        return STATE_NAMES.get(self.state, "unknown")

    @property
    def position(self):
        """Current position tuple."""
        return (self.x, self.y)

    def _record(self, event, order_id):
        """Append an entry to the rider's log."""
        self.log.append({
            "time": _now(),
            "event": event,
            "order_id": order_id,
            "rider_id": self.rider_id,
            "x": self.x,
            "y": self.y,
            "state": self.state,
        })
        limit = _config().get("max_log_entries", 1000)
        if isinstance(limit, int) and limit > 0 and len(self.log) > limit:
            # keep the spawn entry, drop oldest others
            del self.log[1:len(self.log) - limit + 1]

    def _next_order(self):
        """Return the first not yet completed order, cleaning completed ones."""
        while self.orders:
            order = self.orders[0]
            if getattr(order, "status", None) == "completed":
                self.orders.pop(0)
                continue
            return order
        return None

    def _plan_to(self, target):
        self.path = PathPlanner.plan((self.x, self.y), target)
        self.special_case = PathPlanner.is_detour((self.x, self.y), self.path)

    def _advance(self, budget):
        """Move along the planned path using at most ``budget`` units."""
        while budget > 0 and self.path:
            tx, ty = self.path[0]
            dx, dy = tx - self.x, ty - self.y
            if dx == 0 and dy == 0:
                self.path.pop(0)
                continue
            if dx != 0:
                step = min(budget, abs(dx))
                self.x += step if dx > 0 else -step
            else:
                step = min(budget, abs(dy))
                self.y += step if dy > 0 else -step
            budget -= step
            self.distance_travelled += step
            if (self.x, self.y) == (tx, ty):
                self.path.pop(0)
        return budget

    # -------------------------------------------------------------- transitions
    def _accept(self, order):
        """Idle -> picking up."""
        self.current_order = order
        if getattr(order, "rider_id", None) != self.rider_id:
            if hasattr(order, "assign_to"):
                order.assign_to(self.rider_id)
            else:
                order.rider_id = self.rider_id
        order.status = "picking_up"
        order.accept_time = _now()
        self.state = STATE_PICKING_UP
        self._plan_to(order.res_pos)
        self._record("accepted_order", order.id)

    def _arrive_at_merchant(self):
        """Picking up -> delivering."""
        order = self.current_order
        order.status = "delivering"
        order.pickup_time = _now()
        self.state = STATE_DELIVERING
        self._record("arrived_at_merchant", order.id)
        self._plan_to(order.cus_pos)

    def _deliver(self):
        """Delivering -> idle; completes the order."""
        order = self.current_order
        now = _now()
        order.status = "completed"
        order.complete_time = now
        if order in self.orders:
            self.orders.remove(order)
        self.current_order = None
        self.state = STATE_IDLE
        self.special_case = False
        self.path = []
        self.delivered_count += 1
        self._record("delivered_to_customer", order.id)
        funds = globalvar.get_value("funds")
        if isinstance(funds, int):
            globalvar.set_value("funds", funds + int(_config().get("order_revenue", 0)))

    # --------------------------------------------------------------------- tick
    def move(self):
        """Advance the rider by one tick.

        * Idle with pending orders: accept the first order (state -> 1),
          plan the route to the restaurant (no movement this tick).
        * Picking up: move towards the restaurant; on arrival state -> 2.
        * Delivering: move towards the customer; on arrival the order is
          completed, removed from ``orders`` and state -> 0.
        """
        if self.state == STATE_IDLE:
            order = self._next_order()
            if order is None:
                return
            self._accept(order)
            return

        if self.state not in (STATE_PICKING_UP, STATE_DELIVERING):
            self.reset()
            return

        if self.current_order is None or getattr(self.current_order, "status", None) == "completed":
            order = self._next_order()
            if order is None:
                self.state = STATE_IDLE
                self.path = []
                self.current_order = None
                return
            self.current_order = order
            target = order.res_pos if self.state == STATE_PICKING_UP else order.cus_pos
            self._plan_to(target)

        self._advance(self.speed)
        if self.path:
            return
        order = self.current_order
        target = order.res_pos if self.state == STATE_PICKING_UP else order.cus_pos
        if (self.x, self.y) != tuple(target):
            self._plan_to(target)
            return
        if self.state == STATE_PICKING_UP:
            self._arrive_at_merchant()
        else:
            self._deliver()

    def reset(self):
        """Recover from an inconsistent state: back to idle, keep orders."""
        if self.current_order is not None and self.current_order not in self.orders \
                and getattr(self.current_order, "status", None) != "completed":
            self.orders.insert(0, self.current_order)
        self.current_order = None
        self.state = STATE_IDLE
        self.path = []
        self.special_case = False
        self.x, self.y = PathPlanner.snap_to_road(self.x, self.y) \
            if not (0 <= self.x <= 800 and 0 <= self.y <= 800) else (self.x, self.y)

    def remaining_distance(self):
        """Length of the currently planned path."""
        return PathPlanner.path_length((self.x, self.y), self.path)

    def to_dict(self):
        """Serializable representation."""
        return {
            "rider_id": self.rider_id,
            "x": self.x,
            "y": self.y,
            "speed": self.speed,
            "state": self.state,
            "orders": [getattr(o, "id", None) for o in self.orders],
            "special_case": self.special_case,
            "distance_travelled": self.distance_travelled,
            "delivered_count": self.delivered_count,
            "log": list(self.log),
        }

    def __repr__(self):
        return "Rider(id=%d, pos=(%d, %d), state=%s, orders=%d)" % (
            self.rider_id, self.x, self.y, self.state_name, len(self.orders))
