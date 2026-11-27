"""Rider model: movement, state and orders."""

import logging

import globalvar
from config import get_config
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


def _sign(v):
    return (v > 0) - (v < 0)


class Rider:
    """A delivery rider.

    Attributes:
        rider_id: unique identifier.
        x, y: current position.
        speed: units moved per tick.
        state: 0 idle, 1 picking up, 2 delivering.
        orders: list of assigned orders (first one is processed first).
        special_case: True when following a special-case path.
        log: list of event dicts with keys "event" and "order_id" (and more).
    """

    def __init__(self, rider_id, x=None, y=None, speed=None):
        cfg = get_config()
        self.rider_id = rider_id
        self.x = PathPlanner.clamp(cfg.get("spawn_x", 400) if x is None else x)
        self.y = PathPlanner.clamp(cfg.get("spawn_y", 400) if y is None else y)
        self.speed = int(cfg.get("rider_speed", 100) if speed is None else speed)
        if self.speed <= 0:
            self.speed = 1
        self.state = STATE_IDLE
        self.orders = []
        self.special_case = False
        self.path = []
        self.current_order = None
        self.total_distance = 0
        self.completed_orders = 0
        self.log = []
        self._log("spawn", None)

    # ------------------------------------------------------------------
    @property
    def position(self):
        """Current (x, y) position."""
        return (self.x, self.y)

    @property
    def state_name(self):
        """Human readable state."""
        return STATE_NAMES.get(self.state, "unknown")

    def _now(self):
        return globalvar.get_value("time", 0)

    def _log(self, event, order_id):
        self.log.append({
            "event": event,
            "order_id": order_id,
            "time": self._now(),
            "x": self.x,
            "y": self.y,
            "state": self.state,
            "rider_id": self.rider_id,
        })

    def _set_target(self, pos):
        target = (int(pos[0]), int(pos[1]))
        self.special_case = PathPlanner.is_special_case(self.position, target)
        self.path = PathPlanner.plan_path(self.position, target)

    def projected_position(self):
        """Position where the rider will be after finishing all orders."""
        if self.orders:
            return tuple(self.orders[-1].cus_pos)
        return self.position

    def remaining_path(self):
        """Waypoints still to travel for the current order and queue."""
        return list(self.path)

    # ------------------------------------------------------------------
    def move(self):
        """Advance the rider by one tick.

        Handles state transitions (accepting orders, arriving at the
        merchant, delivering to the customer) and logs them.
        """
        if self.state == STATE_IDLE:
            if not self.orders:
                return
            order = self.orders[0]
            self.current_order = order
            self.state = STATE_PICKING_UP
            if hasattr(order, "mark_accepted"):
                order.mark_accepted(self._now())
            self._set_target(order.res_pos)
            self._log("accepted_order", order.id)

        # Consistency recovery
        if self.current_order is None or self.current_order not in self.orders:
            self.current_order = None
            self.state = STATE_IDLE
            self.path = []
            self.special_case = False
            return

        remaining = self.speed
        guard = 0
        while remaining > 0 and self.path and guard < 64:
            guard += 1
            wx, wy = self.path[0]
            dx = wx - self.x
            dy = wy - self.y
            if dx == 0 and dy == 0:
                self.path.pop(0)
                continue
            if dx != 0:
                step = min(abs(dx), remaining)
                self.x += step * _sign(dx)
            else:
                step = min(abs(dy), remaining)
                self.y += step * _sign(dy)
            remaining -= step
            self.total_distance += step
            if (self.x, self.y) == (wx, wy):
                self.path.pop(0)

        if not self.path:
            self._on_arrival()

    def _on_arrival(self):
        order = self.current_order
        now = self._now()
        if self.state == STATE_PICKING_UP:
            self.state = STATE_DELIVERING
            if hasattr(order, "mark_picked_up"):
                order.mark_picked_up(now)
            self._log("arrived_at_merchant", order.id)
            self._set_target(order.cus_pos)
        elif self.state == STATE_DELIVERING:
            if hasattr(order, "complete"):
                order.complete(now, self.rider_id)
            else:
                order.status = "completed"
            fee = int(getattr(order, "fee", 0) or 0)
            globalvar.set_value("funds", globalvar.get_value("funds", 0) + fee)
            if order in self.orders:
                self.orders.remove(order)
            self.current_order = None
            self.state = STATE_IDLE
            self.special_case = False
            self.path = []
            self.completed_orders += 1
            self._log("delivered_to_customer", order.id)

    def to_dict(self):
        """Serialisable representation."""
        return {
            "rider_id": self.rider_id,
            "x": self.x,
            "y": self.y,
            "speed": self.speed,
            "state": self.state,
            "orders": [o.id for o in self.orders],
            "special_case": self.special_case,
            "total_distance": self.total_distance,
            "completed_orders": self.completed_orders,
            "log": list(self.log),
        }

    def __repr__(self):
        return "Rider(id=%s, pos=(%d,%d), state=%s, orders=%s)" % (
            self.rider_id, self.x, self.y, self.state_name,
            [o.id for o in self.orders])
