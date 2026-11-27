"""Rider model: movement, state machine and status log."""

import logging

import globalvar
from path_planner import PathPlanner, Route, MAP_SIZE

logger = logging.getLogger(__name__)

DEFAULT_SPEED = 20


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


def _now():
    return globalvar.get_value("tick", 0) or 0


class Rider:
    """A delivery rider.

    Attributes:
        rider_id: unique id.
        x, y: current position (always on a street).
        speed: units per tick.
        state: 0 idle, 1 picking up, 2 delivering.
        orders: assigned orders (served first-in first-out).
        special_case: True while a detour around the target is required.
        log: list of event dicts with keys "event", "order_id", "time",
            "x", "y", "state".
    """

    def __init__(self, rider_id, x=None, y=None, speed=None):
        self.rider_id = rider_id
        if x is None or y is None:
            x = (rider_id * 300) % MAP_SIZE
            y = (rider_id * 500) % MAP_SIZE
        x, y = PathPlanner.nearest_street_point(PathPlanner.clamp(x),
                                                PathPlanner.clamp(y))
        self.x = x
        self.y = y
        if speed is None:
            speed = globalvar.get_value("rider_speed", DEFAULT_SPEED) or DEFAULT_SPEED
        self.speed = int(speed)
        self.state = RiderState.IDLE
        self.orders = []
        self.special_case = False
        self.log = []
        self.delivered_count = 0
        self.distance_travelled = 0
        self._acknowledged = set()
        self._log_event("spawn", None)

    # ------------------------------------------------------------------ utils
    @property
    def position(self):
        """Current (x, y)."""
        return self.x, self.y

    def _log_event(self, event, order_id):
        self.log.append({
            "event": event,
            "order_id": order_id,
            "time": _now(),
            "x": self.x,
            "y": self.y,
            "state": self.state,
        })

    def current_order(self):
        """Order currently being served, or None."""
        return self.orders[0] if self.orders else None

    def current_target(self):
        """Street point the rider is currently heading to (or None)."""
        order = self.current_order()
        if order is None:
            return None
        if self.state == RiderState.DELIVERING:
            return PathPlanner.access_point(order.cus_pos)
        return PathPlanner.access_point(order.res_pos)

    def remaining_targets(self):
        """All remaining stops in order of service."""
        targets = []
        for i, order in enumerate(self.orders):
            if not (i == 0 and self.state == RiderState.DELIVERING):
                targets.append(PathPlanner.access_point(order.res_pos))
            targets.append(PathPlanner.access_point(order.cus_pos))
        return targets

    def planned_route(self):
        """Return the full :class:`Route` through all remaining stops."""
        return PathPlanner.plan_multi(self.position, self.remaining_targets(),
                                      self.speed)

    def final_position(self):
        """Position after finishing all assigned orders."""
        targets = self.remaining_targets()
        return targets[-1] if targets else self.position

    def remaining_work(self):
        """Remaining travel distance for all assigned orders."""
        return self.planned_route().length

    # --------------------------------------------------------------- movement
    def _advance(self, waypoints):
        remaining = self.speed
        for tx, ty in waypoints:
            if remaining <= 0:
                break
            dx = tx - self.x
            dy = ty - self.y
            dist = abs(dx) + abs(dy)
            if dist <= remaining:
                self.x, self.y = tx, ty
                remaining -= dist
                self.distance_travelled += dist
            else:
                if dx != 0:
                    self.x += remaining if dx > 0 else -remaining
                else:
                    self.y += remaining if dy > 0 else -remaining
                self.distance_travelled += remaining
                remaining = 0

    def move(self):
        """Advance the rider by one tick.

        Handles acknowledgement of new orders, state transitions, movement
        along streets and order completion, logging every key event.
        """
        # Drop orders completed elsewhere.
        for order in list(self.orders):
            if getattr(order, "status", None) == "completed":
                self.orders.remove(order)
                self._acknowledged.discard(order.id)

        for order in self.orders:
            if order.id not in self._acknowledged:
                self._acknowledged.add(order.id)
                if getattr(order, "rider_id", None) is None:
                    order.assign_to(self.rider_id)
                self._log_event("accepted_order", order.id)

        if not self.orders:
            self.state = RiderState.IDLE
            self.special_case = False
            return

        order = self.orders[0]
        if self.state == RiderState.IDLE:
            self.state = RiderState.PICKING_UP
            order.mark_picking_up()

        target = self.current_target()
        waypoints, special = PathPlanner.plan(self.position, target)
        if special:
            self.special_case = True
        self._advance(waypoints[1:])

        if self.position == tuple(target):
            now = _now()
            if self.state == RiderState.PICKING_UP:
                self.state = RiderState.DELIVERING
                self.special_case = False
                order.mark_picked_up(now)
                self._log_event("arrived_at_merchant", order.id)
            else:
                order.complete(now)
                self.orders.pop(0)
                self._acknowledged.discard(order.id)
                self.state = RiderState.IDLE
                self.special_case = False
                self.delivered_count += 1
                self._log_event("delivered_to_customer", order.id)

    # ---------------------------------------------------------- persistence
    def to_dict(self):
        """Serialise to a JSON friendly dict."""
        return {
            "rider_id": self.rider_id,
            "x": self.x,
            "y": self.y,
            "speed": self.speed,
            "state": self.state,
            "orders": [o.id for o in self.orders],
            "special_case": self.special_case,
            "log": list(self.log),
            "delivered_count": self.delivered_count,
            "distance_travelled": self.distance_travelled,
            "acknowledged": sorted(self._acknowledged),
        }

    @classmethod
    def from_dict(cls, data, orders_by_id=None):
        """Rebuild a rider from :meth:`to_dict` output."""
        orders_by_id = orders_by_id or {}
        obj = cls.__new__(cls)
        obj.rider_id = int(data["rider_id"])
        obj.x = int(data["x"])
        obj.y = int(data["y"])
        obj.speed = int(data.get("speed", DEFAULT_SPEED))
        obj.state = int(data.get("state", 0))
        obj.orders = [orders_by_id[i] for i in data.get("orders", [])
                      if i in orders_by_id]
        obj.special_case = bool(data.get("special_case", False))
        obj.log = list(data.get("log", []))
        obj.delivered_count = int(data.get("delivered_count", 0))
        obj.distance_travelled = int(data.get("distance_travelled", 0))
        obj._acknowledged = set(data.get("acknowledged", []))
        return obj

    def __repr__(self):
        return "Rider(id=%s, pos=(%d, %d), state=%s, orders=%d)" % (
            self.rider_id, self.x, self.y, RiderState.name(self.state),
            len(self.orders))
