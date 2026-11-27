"""Rider model: movement, state machine and status log."""

import logging

import globalvar
from path_planner import PathPlanner

logger = logging.getLogger(__name__)

START_X = 435
START_Y = 385
DEFAULT_SPEED = 10


class RiderState:
    """Rider state enumeration."""

    IDLE = 0
    PICKING_UP = 1
    DELIVERING = 2

    NAMES = {0: "idle", 1: "picking up", 2: "delivering"}

    @classmethod
    def name(cls, state):
        """Human readable name of a state."""
        return cls.NAMES.get(state, "unknown")


def _order_id(order):
    return getattr(order, "id", id(order))


class Rider:
    """A delivery rider.

    Orders are assigned by appending them to ``rider.orders``; the rider
    notices them on the next :meth:`move` call.
    """

    def __init__(self, rider_id, x=START_X, y=START_Y, speed=None):
        if speed is None:
            speed = globalvar.get_value("rider_speed", DEFAULT_SPEED)
        self.rider_id = rider_id
        self.x = int(x)
        self.y = int(y)
        self.speed = int(speed)
        self.state = RiderState.IDLE
        self.orders = []
        self.special_case = False
        self.log = []
        self.route = []
        self.current_order = None
        self.distance_travelled = 0
        self._acknowledged = set()
        self._local_time = 0
        self._record("spawn", None)

    # ------------------------------------------------------------------ utils
    def _now(self):
        t = globalvar.get_value("tick")
        return t if t is not None else self._local_time

    def _record(self, event, order_id):
        entry = {
            "event": event,
            "order_id": order_id,
            "time": self._now(),
            "x": self.x,
            "y": self.y,
            "state": self.state,
        }
        self.log.append(entry)
        logger.debug("Rider %s: %s", self.rider_id, entry)

    def _plan_to(self, target):
        route = PathPlanner.plan((self.x, self.y), target, self.speed)
        self.route = list(route.waypoints[1:])
        self.special_case = route.special_case

    @property
    def position(self):
        """Current (x, y) position."""
        return (self.x, self.y)

    @property
    def state_name(self):
        """Human readable state."""
        return RiderState.name(self.state)

    def is_idle(self):
        """True if the rider is idle and has no queued orders."""
        return self.state == RiderState.IDLE and not self.orders

    # --------------------------------------------------------------- movement
    def move(self):
        """Advance the rider by one tick.

        Handles new-order acceptance, movement along the planned route and
        all state transitions (with their log entries).
        """
        self._local_time += 1
        self._acknowledge_new_orders()

        if self.current_order is not None and self.current_order not in self.orders:
            # Order was removed externally; recover to a consistent state.
            self.current_order = None
            self.route = []
            self.state = RiderState.IDLE
            self.special_case = False

        if self.state == RiderState.IDLE:
            if not self.orders:
                return
            self._start_pickup(self.orders[0])

        self._advance()
        self._check_arrival()

    def _acknowledge_new_orders(self):
        for order in self.orders:
            oid = _order_id(order)
            if oid in self._acknowledged:
                continue
            self._acknowledged.add(oid)
            if getattr(order, "status", None) == "pending":
                order.status = "assigned"
            if getattr(order, "rider_id", None) is None:
                try:
                    order.rider_id = self.rider_id
                except AttributeError:
                    pass
            self._record("accepted_order", oid)

    def _start_pickup(self, order):
        self.current_order = order
        self.state = RiderState.PICKING_UP
        if hasattr(order, "status"):
            order.status = "picking_up"
        self._plan_to(tuple(order.res_pos))

    def _advance(self):
        budget = self.speed
        while budget > 0 and self.route:
            tx, ty = self.route[0]
            dx = tx - self.x
            dy = ty - self.y
            if dx == 0 and dy == 0:
                self.route.pop(0)
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
                self.route.pop(0)

    def _check_arrival(self):
        if self.route:
            return
        order = self.current_order
        if order is None:
            self.state = RiderState.IDLE
            return
        if self.state == RiderState.PICKING_UP:
            self.state = RiderState.DELIVERING
            if hasattr(order, "status"):
                order.status = "delivering"
            try:
                order.pickup_time = self._now()
            except AttributeError:
                pass
            self._record("arrived_at_merchant", _order_id(order))
            self._plan_to(tuple(order.cus_pos))
            if self.route:
                return
        if self.state == RiderState.DELIVERING and not self.route:
            self._deliver(order)

    def _deliver(self, order):
        now = self._now()
        try:
            order.status = "completed"
            order.completion_time = now
            start = getattr(order, "start_time", None)
            if start is not None:
                order.time_taken = now - start
        except AttributeError:
            pass
        if order in self.orders:
            self.orders.remove(order)
        self.current_order = None
        self.state = RiderState.IDLE
        self.special_case = False
        self._record("delivered_to_customer", _order_id(order))

    # ------------------------------------------------------------ persistence
    def to_dict(self):
        """Serialise rider to a JSON-compatible dict."""
        return {
            "rider_id": self.rider_id,
            "x": self.x,
            "y": self.y,
            "speed": self.speed,
            "state": self.state,
            "orders": [_order_id(o) for o in self.orders],
            "current_order": (_order_id(self.current_order)
                              if self.current_order is not None else None),
            "special_case": self.special_case,
            "route": [list(p) for p in self.route],
            "log": list(self.log),
            "distance_travelled": self.distance_travelled,
            "acknowledged": sorted(self._acknowledged),
            "local_time": self._local_time,
        }

    @classmethod
    def from_dict(cls, data, orders_by_id):
        """Rebuild a rider from :meth:`to_dict` output."""
        r = cls.__new__(cls)
        r.rider_id = data["rider_id"]
        r.x = int(data["x"])
        r.y = int(data["y"])
        r.speed = int(data.get("speed", DEFAULT_SPEED))
        r.state = int(data.get("state", 0))
        r.orders = [orders_by_id[i] for i in data.get("orders", [])
                    if i in orders_by_id]
        cur = data.get("current_order")
        r.current_order = orders_by_id.get(cur) if cur is not None else None
        r.special_case = bool(data.get("special_case", False))
        r.route = [tuple(p) for p in data.get("route", [])]
        r.log = list(data.get("log", []))
        r.distance_travelled = data.get("distance_travelled", 0)
        r._acknowledged = set(data.get("acknowledged", []))
        r._local_time = data.get("local_time", 0)
        return r

    def __repr__(self):
        return "Rider(id=%s, pos=(%s, %s), state=%s, orders=%d)" % (
            self.rider_id, self.x, self.y, self.state, len(self.orders))
