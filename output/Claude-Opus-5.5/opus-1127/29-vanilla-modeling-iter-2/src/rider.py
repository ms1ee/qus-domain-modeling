"""Rider model: movement, state transitions and status log."""

import logging

import globalvar
from path_planner import PathPlanner

logger = logging.getLogger(__name__)

DEFAULT_START = (435, 385)
DEFAULT_SPEED = 10


class RiderState:
    """Rider state enumeration."""

    IDLE = 0
    PICKING_UP = 1
    DELIVERING = 2

    NAMES = {0: "idle", 1: "picking up", 2: "delivering"}

    @classmethod
    def name(cls, state):
        """Return a human readable state name."""
        return cls.NAMES.get(state, "unknown")


def _now():
    return globalvar.get_value("current_tick", 0)


def _order_id(order):
    return getattr(order, "id", None)


class Rider:
    """A delivery rider.

    Orders are assigned by appending them to ``rider.orders``; ``move()``
    advances the rider by one tick and performs state transitions.
    """

    def __init__(self, rider_id, x=None, y=None, speed=None):
        start = globalvar.get_value("rider_start", DEFAULT_START) or DEFAULT_START
        self.rider_id = rider_id
        self.x = int(start[0]) if x is None else int(x)
        self.y = int(start[1]) if y is None else int(y)
        self.speed = int(globalvar.get_value("rider_speed", DEFAULT_SPEED)
                         if speed is None else speed)
        self.state = RiderState.IDLE
        self.orders = []
        self.special_case = False
        self.path = []
        self.log = []
        self._planner = PathPlanner()
        self._record("spawn", None)

    # ------------------------------------------------------------------
    def _record(self, event, order):
        entry = {
            "time": _now(),
            "event": event,
            "order_id": _order_id(order) if order is not None else None,
            "x": self.x,
            "y": self.y,
            "state": self.state,
        }
        self.log.append(entry)
        logger.debug("Rider %s: %s", self.rider_id, entry)

    def _plan_to(self, target):
        target = (int(target[0]), int(target[1]))
        self.special_case = PathPlanner.is_directly_vertical((self.x, self.y), target)
        pts = self._planner.plan((self.x, self.y), target)
        self.path = pts[1:]

    @property
    def current_order(self):
        """Order currently being processed (None if idle)."""
        if self.state != RiderState.IDLE and self.orders:
            return self.orders[0]
        return None

    @property
    def position(self):
        """Current (x, y) position."""
        return self.x, self.y

    def is_idle(self):
        """Return True if the rider is idle with no queued orders."""
        return self.state == RiderState.IDLE and not self.orders

    # ------------------------------------------------------------------
    def move(self):
        """Advance the rider one tick."""
        if self.state != RiderState.IDLE and not self.orders:
            # Consistency recovery: busy without orders.
            logger.warning("Rider %s busy without orders; resetting", self.rider_id)
            self.state = RiderState.IDLE
            self.path = []
            self.special_case = False

        if self.state == RiderState.IDLE:
            if not self.orders:
                return
            self._start_order(self.orders[0])

        self._advance()
        if not self.path:
            self._on_arrival()

    def _start_order(self, order):
        self.state = RiderState.PICKING_UP
        if getattr(order, "rider_id", None) is None and hasattr(order, "assign_to"):
            order.assign_to(self.rider_id)
        if hasattr(order, "status"):
            order.status = "picking_up"
        if hasattr(order, "accept_time"):
            order.accept_time = _now()
        self._plan_to(order.res_pos)
        self._record("accepted_order", order)

    def _advance(self):
        remaining = self.speed
        while remaining > 0 and self.path:
            tx, ty = self.path[0]
            if self.x != tx:
                step = min(remaining, abs(tx - self.x))
                self.x += step if tx > self.x else -step
                remaining -= step
            elif self.y != ty:
                step = min(remaining, abs(ty - self.y))
                self.y += step if ty > self.y else -step
                remaining -= step
            if (self.x, self.y) == (tx, ty):
                self.path.pop(0)

    def _on_arrival(self):
        order = self.orders[0]
        if self.state == RiderState.PICKING_UP:
            self.state = RiderState.DELIVERING
            if hasattr(order, "status"):
                order.status = "delivering"
            if hasattr(order, "pickup_time"):
                order.pickup_time = _now()
            self._record("arrived_at_merchant", order)
            self._plan_to(order.cus_pos)
        elif self.state == RiderState.DELIVERING:
            now = _now()
            if hasattr(order, "complete"):
                order.complete(now)
            else:
                order.status = "completed"
            self.orders.pop(0)
            self.state = RiderState.IDLE
            self.path = []
            self.special_case = False
            self._record("delivered_to_customer", order)

    # ------------------------------------------------------------------
    def planned_waypoints(self):
        """Return the full remaining route covering all assigned orders."""
        points = [(self.x, self.y)] + list(self.path)
        queued = list(self.orders)
        if self.state == RiderState.PICKING_UP and queued:
            current = queued.pop(0)
            points.extend(self._planner.plan(points[-1], current.cus_pos)[1:])
        elif self.state == RiderState.DELIVERING and queued:
            queued.pop(0)
        for order in queued:
            points.extend(self._planner.plan_multi(points[-1],
                                                   [order.res_pos, order.cus_pos])[1:])
        return points

    def to_dict(self):
        """Serialise the rider to a JSON-friendly dict."""
        return {
            "rider_id": self.rider_id,
            "x": self.x,
            "y": self.y,
            "speed": self.speed,
            "state": int(self.state),
            "special_case": bool(self.special_case),
            "order_ids": [_order_id(o) for o in self.orders],
            "path": [list(p) for p in self.path],
            "log": list(self.log),
        }

    @classmethod
    def from_dict(cls, data, orders_by_id=None):
        """Rebuild a rider from :meth:`to_dict` output."""
        rider = cls.__new__(cls)
        rider.rider_id = data["rider_id"]
        rider.x = int(data["x"])
        rider.y = int(data["y"])
        rider.speed = int(data.get("speed", DEFAULT_SPEED))
        rider.state = int(data.get("state", 0))
        rider.special_case = bool(data.get("special_case", False))
        orders_by_id = orders_by_id or {}
        rider.orders = [orders_by_id[i] for i in data.get("order_ids", [])
                        if i in orders_by_id]
        rider.path = [tuple(p) for p in data.get("path", [])]
        rider.log = list(data.get("log", []))
        rider._planner = PathPlanner()
        return rider

    def __repr__(self):
        return "Rider(id=%s, pos=(%s,%s), state=%s, orders=%d)" % (
            self.rider_id, self.x, self.y, self.state, len(self.orders))
