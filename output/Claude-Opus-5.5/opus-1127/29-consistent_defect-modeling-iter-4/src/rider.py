"""Rider model: movement, state machine and status history."""

import globalvar
from path_planner import PathPlanner


class RiderState:
    """Rider status enumeration."""
    IDLE = 0
    PICKING_UP = 1
    DELIVERING = 2

    NAMES = {0: "idle", 1: "picking up", 2: "delivering"}

    @classmethod
    def name(cls, state):
        """Human readable state name."""
        return cls.NAMES.get(state, "unknown")


DEFAULT_SPEED = 20
DEFAULT_START = (400, 400)

_planner = PathPlanner()


def _current_time(fallback):
    value = globalvar.get_value("current_tick")
    return fallback if value is None else value


class Rider:
    """A delivery rider.

    Orders are assigned by appending them to ``rider.orders``.  Calling
    :meth:`move` advances the rider by one simulation tick.
    """

    def __init__(self, rider_id, x=None, y=None, speed=None):
        cfg = globalvar.get_value("config") or {}
        self.rider_id = rider_id
        start = cfg.get("rider_start", DEFAULT_START)
        self.x = int(start[0]) if x is None else int(x)
        self.y = int(start[1]) if y is None else int(y)
        self.speed = int(cfg.get("rider_speed", DEFAULT_SPEED)) \
            if speed is None else int(speed)
        self.state = RiderState.IDLE
        self.orders = []
        self.special_case = False
        self.current_order = None
        self.waypoints = []
        self.total_distance = 0
        self._ticks = 0
        self.log = []
        self._record("spawn", None)

    # ------------------------------------------------------------------
    def _record(self, event, order_id):
        self.log.append({
            "event": event,
            "order_id": order_id,
            "time": _current_time(self._ticks),
            "x": self.x,
            "y": self.y,
            "state": self.state,
        })

    def active_orders(self):
        """Return unique, not yet completed orders."""
        seen = set()
        result = []
        for order in self.orders:
            if id(order) in seen:
                continue
            seen.add(id(order))
            if getattr(order, "status", None) != "completed":
                result.append(order)
        return result

    def is_idle(self):
        """True when the rider has nothing to do."""
        return self.state == RiderState.IDLE and not self.active_orders()

    def target(self):
        """Current target coordinates, or None."""
        order = self.current_order
        if order is None:
            return None
        if self.state == RiderState.PICKING_UP:
            return tuple(order.res_pos)
        if self.state == RiderState.DELIVERING:
            return tuple(order.cus_pos)
        return None

    def _plan(self):
        tgt = self.target()
        if tgt is None:
            self.waypoints = []
            return
        points, special = _planner.plan_points((self.x, self.y), tgt)
        self.special_case = special
        self.waypoints = points[1:]

    def _start_next_order(self):
        pending = self.active_orders()
        if not pending:
            self.current_order = None
            self.state = RiderState.IDLE
            self.waypoints = []
            return False
        order = pending[0]
        self.current_order = order
        if getattr(order, "rider_id", None) is None:
            order.rider_id = self.rider_id
        if getattr(order, "status", None) == "pending":
            order.status = "assigned"
        if getattr(order, "accept_time", None) is None:
            try:
                order.accept_time = _current_time(self._ticks)
            except AttributeError:
                pass
        self.state = RiderState.PICKING_UP
        self._record("accepted_order", order.id)
        self._plan()
        return True

    def move(self):
        """Advance the rider by one tick, handling state transitions."""
        self._ticks += 1
        if self.current_order is None or \
                getattr(self.current_order, "status", None) == "completed":
            self.current_order = None
            if not self._start_next_order():
                return
        if not self.waypoints and (self.x, self.y) != self.target():
            self._plan()
        self.x, self.y, travelled = PathPlanner.advance_along(
            self.x, self.y, self.waypoints, self.speed)
        self.total_distance += travelled
        if (self.x, self.y) != self.target():
            return
        order = self.current_order
        if self.state == RiderState.PICKING_UP:
            self.state = RiderState.DELIVERING
            order.status = "picked_up"
            self._record("arrived_at_merchant", order.id)
            self._plan()
        elif self.state == RiderState.DELIVERING:
            now = _current_time(self._ticks)
            if hasattr(order, "complete"):
                order.complete(now)
            else:
                order.status = "completed"
            self._record("delivered_to_customer", order.id)
            self.current_order = None
            self.waypoints = []
            self.special_case = False
            if not self._start_next_order():
                self.state = RiderState.IDLE

    # ------------------------------------------------------------------
    def to_dict(self):
        """Serialise rider to a dictionary."""
        return {
            "rider_id": self.rider_id,
            "x": self.x,
            "y": self.y,
            "speed": self.speed,
            "state": self.state,
            "special_case": self.special_case,
            "order_ids": [o.id for o in self.orders],
            "current_order_id": self.current_order.id
            if self.current_order else None,
            "waypoints": [list(p) for p in self.waypoints],
            "total_distance": self.total_distance,
            "ticks": self._ticks,
            "log": list(self.log),
        }

    @classmethod
    def from_dict(cls, data, orders_by_id):
        """Rebuild a rider from :meth:`to_dict` output."""
        rider = cls.__new__(cls)
        rider.rider_id = data["rider_id"]
        rider.x = data["x"]
        rider.y = data["y"]
        rider.speed = data["speed"]
        rider.state = data["state"]
        rider.special_case = data.get("special_case", False)
        rider.orders = [orders_by_id[i] for i in data.get("order_ids", [])
                        if i in orders_by_id]
        cid = data.get("current_order_id")
        rider.current_order = orders_by_id.get(cid) if cid is not None \
            else None
        rider.waypoints = [tuple(p) for p in data.get("waypoints", [])]
        rider.total_distance = data.get("total_distance", 0)
        rider._ticks = data.get("ticks", 0)
        rider.log = list(data.get("log", []))
        return rider

    def __repr__(self):
        return "Rider(id=%s, pos=(%s, %s), state=%s, orders=%d)" % (
            self.rider_id, self.x, self.y, RiderState.name(self.state),
            len(self.orders))
