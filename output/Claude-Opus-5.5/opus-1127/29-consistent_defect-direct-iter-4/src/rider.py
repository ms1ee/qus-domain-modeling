"""Rider model: movement, state machine and order handling."""

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

DEFAULT_START = (400, 400)
DEFAULT_SPEED = 20


class Rider:
    """A delivery rider.

    Attributes:
        rider_id: unique identifier.
        x, y: current position.
        speed: units moved per tick.
        state: 0 idle, 1 picking up, 2 delivering.
        orders: all orders assigned to the rider (including history).
        special_case: True while moving straight up/down to a target.
        log: list of event dicts with keys "event" and "order_id".
    """

    def __init__(self, rider_id):
        self.rider_id = rider_id
        cfg = globalvar.get_value("config") or {}
        start = cfg.get("rider_start", DEFAULT_START)
        self.x = int(start[0])
        self.y = int(start[1])
        self.speed = int(cfg.get("rider_speed", DEFAULT_SPEED))
        self.state = STATE_IDLE
        self.orders = []
        self.special_case = False
        self.route = []
        self.total_distance = 0
        self.log = []
        self._log("spawn", None)

    # ------------------------------------------------------------------
    def _log(self, event, order_id):
        entry = {
            "event": event,
            "order_id": order_id,
            "time": globalvar.get_value("time", 0),
            "x": self.x,
            "y": self.y,
            "state": self.state,
        }
        self.log.append(entry)
        logger.debug("Rider %s: %s", self.rider_id, entry)

    @property
    def position(self):
        """Current (x, y) position."""
        return (self.x, self.y)

    @property
    def state_name(self):
        """Human readable state."""
        return STATE_NAMES.get(self.state, "unknown")

    def current_order(self):
        """Return the first not-yet-completed order, or None."""
        for order in self.orders:
            if getattr(order, "status", None) != "completed":
                return order
        return None

    def active_orders(self):
        """Return all orders that are not completed."""
        return [o for o in self.orders
                if getattr(o, "status", None) != "completed"]

    def is_idle(self):
        """True if the rider is idle with no outstanding work."""
        return self.state == STATE_IDLE and self.current_order() is None

    def _plan(self, target):
        self.route = PathPlanner.plan_route((self.x, self.y), target)
        self.special_case = PathPlanner.is_vertical_special(
            (self.x, self.y), target)

    def _accept(self, order):
        now = globalvar.get_value("time", 0)
        self.state = STATE_PICKING_UP
        if getattr(order, "rider_id", None) is None:
            order.rider_id = self.rider_id
        order.status = "picking_up"
        order.accepted_time = now
        self._log("accepted_order", order.id)
        self._plan(order.res_pos)

    # ------------------------------------------------------------------
    def move(self):
        """Advance the rider by one tick.

        Handles accepting new orders, moving along the planned route,
        and state transitions on arrival at the restaurant/customer.
        """
        order = self.current_order()
        if order is None:
            if self.state != STATE_IDLE:
                self.state = STATE_IDLE
            self.route = []
            self.special_case = False
            return

        if self.state == STATE_IDLE:
            self._accept(order)

        target = tuple(order.res_pos) if self.state == STATE_PICKING_UP \
            else tuple(order.cus_pos)
        if not self.route or tuple(self.route[-1]) != target:
            if (self.x, self.y) != target:
                self._plan(target)

        self.x, self.y, self.route, moved = PathPlanner.advance(
            self.x, self.y, self.route, self.speed)
        self.total_distance += moved
        order.distance = getattr(order, "distance", 0) + moved

        if (self.x, self.y) != target:
            return

        now = globalvar.get_value("time", 0)
        self.special_case = False
        if self.state == STATE_PICKING_UP:
            self.state = STATE_DELIVERING
            order.status = "delivering"
            order.picked_time = now
            self._log("arrived_at_merchant", order.id)
            self._plan(tuple(order.cus_pos))
        elif self.state == STATE_DELIVERING:
            order.status = "completed"
            order.completed_time = now
            self._log("delivered_to_customer", order.id)
            self.route = []
            next_order = self.current_order()
            if next_order is not None:
                self._accept(next_order)
            else:
                self.state = STATE_IDLE

    # ------------------------------------------------------------------
    def to_dict(self):
        """Serialise rider data to a JSON compatible dict."""
        return {
            "rider_id": self.rider_id,
            "x": self.x,
            "y": self.y,
            "speed": self.speed,
            "state": self.state,
            "special_case": self.special_case,
            "route": [list(p) for p in self.route],
            "total_distance": self.total_distance,
            "order_ids": [o.id for o in self.orders],
            "log": list(self.log),
        }

    @classmethod
    def from_dict(cls, data, orders_by_id):
        """Rebuild a rider from serialised data."""
        rider = cls.__new__(cls)
        rider.rider_id = data["rider_id"]
        rider.x = int(data["x"])
        rider.y = int(data["y"])
        rider.speed = int(data.get("speed", DEFAULT_SPEED))
        rider.state = int(data.get("state", STATE_IDLE))
        rider.special_case = bool(data.get("special_case", False))
        rider.route = [tuple(p) for p in data.get("route", [])]
        rider.total_distance = data.get("total_distance", 0)
        rider.orders = [orders_by_id[i] for i in data.get("order_ids", [])
                        if i in orders_by_id]
        rider.log = list(data.get("log", []))
        return rider

    def __repr__(self):
        return "Rider(id=%s, pos=(%s, %s), state=%s, orders=%d)" % (
            self.rider_id, self.x, self.y, self.state_name, len(self.orders))
