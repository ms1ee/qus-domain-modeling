"""Rider model: movement, state machine and status-change log."""

import logging

import globalvar
from path_planner import PathPlanner

logger = logging.getLogger(__name__)

DEFAULT_SPAWN = (435, 385)
DEFAULT_SPEED = 10
MAX_LOG_ENTRIES = 5000


class RiderState:
    """Rider state enumeration."""
    IDLE = 0
    PICKING_UP = 1
    DELIVERING = 2

    NAMES = {0: "idle", 1: "picking up", 2: "delivering"}

    @classmethod
    def name(cls, state):
        """Human readable state name."""
        return cls.NAMES.get(state, "unknown")


class Rider:
    """A delivery rider.

    Orders are assigned by appending them to :attr:`orders`; :meth:`move`
    advances the rider by one tick and performs the state transitions.
    """

    def __init__(self, rider_id, x=None, y=None, speed=None):
        cfg = globalvar.get_value("config") or {}
        self.rider_id = rider_id
        self.x = int(x if x is not None else cfg.get("spawn_x", DEFAULT_SPAWN[0]))
        self.y = int(y if y is not None else cfg.get("spawn_y", DEFAULT_SPAWN[1]))
        self.speed = int(speed if speed is not None else cfg.get("rider_speed", DEFAULT_SPEED))
        self.state = RiderState.IDLE
        self.orders = []
        self.special_case = False
        self.log = []
        self.delivered_count = 0
        self._accepted_ids = set()
        self._waypoints = []
        self._route_target = None
        self._record("spawn", None)

    # ------------------------------------------------------------------ utils
    @property
    def id(self):
        """Alias for :attr:`rider_id`."""
        return self.rider_id

    @staticmethod
    def _now():
        return globalvar.get_value("tick", 0) or 0

    def _record(self, event, order_id, from_state=None):
        entry = {
            "time": self._now(),
            "event": event,
            "order_id": order_id,
            "x": self.x,
            "y": self.y,
            "state": self.state,
            "from_state": from_state if from_state is not None else self.state,
            "to_state": self.state,
        }
        self.log.append(entry)
        if len(self.log) > MAX_LOG_ENTRIES:
            del self.log[:len(self.log) - MAX_LOG_ENTRIES]
        logger.debug("Rider %s: %s", self.rider_id, entry)

    def _set_state(self, new_state):
        old = self.state
        self.state = new_state
        return old

    def is_idle(self):
        """Return True if the rider is idle without pending orders."""
        return self.state == RiderState.IDLE and not self.orders

    def distance_to(self, x, y):
        """Euclidean distance from the rider to a point."""
        return ((self.x - x) ** 2 + (self.y - y) ** 2) ** 0.5

    # --------------------------------------------------------------- movement
    def _accept_new_orders(self):
        for order in self.orders:
            oid = getattr(order, "id", None)
            if oid in self._accepted_ids:
                continue
            self._accepted_ids.add(oid)
            if getattr(order, "rider_id", None) != self.rider_id and hasattr(order, "assign_to"):
                order.assign_to(self.rider_id)
            self._record("accepted_order", oid)

    def _current_target(self, order):
        if self.state == RiderState.DELIVERING:
            return tuple(order.cus_pos)
        return tuple(order.res_pos)

    def _arrive(self, order):
        tick = self._now()
        if self.state == RiderState.PICKING_UP:
            old = self._set_state(RiderState.DELIVERING)
            order.mark_picked_up(tick)
            self._waypoints = []
            self._route_target = None
            self._record("arrived_at_merchant", order.id, from_state=old)
        else:
            old = self._set_state(RiderState.IDLE)
            order.mark_completed(tick)
            if self.orders and self.orders[0] is order:
                self.orders.pop(0)
            else:
                try:
                    self.orders.remove(order)
                except ValueError:
                    pass
            self._accepted_ids.discard(order.id)
            self.delivered_count += 1
            self._waypoints = []
            self._route_target = None
            self.special_case = False
            self._record("delivered_to_customer", order.id, from_state=old)

    def _advance(self, target, budget):
        if self._route_target != target or not self._waypoints:
            points, special = PathPlanner.plan_points((self.x, self.y), target)
            self._waypoints = list(points[1:])
            self._route_target = target
            self.special_case = special
        while budget > 0 and self._waypoints:
            wx, wy = self._waypoints[0]
            if self.x == wx and self.y == wy:
                self._waypoints.pop(0)
                continue
            if self.x != wx:
                step = min(budget, abs(wx - self.x))
                self.x += step if wx > self.x else -step
            else:
                step = min(budget, abs(wy - self.y))
                self.y += step if wy > self.y else -step
            budget -= step
            if self.x == wx and self.y == wy:
                self._waypoints.pop(0)
        if not self._waypoints and (self.x, self.y) != target:
            self._route_target = None
        return budget

    def move(self):
        """Advance the rider by one tick.

        Handles order acceptance, movement along the planned path and the
        state transitions idle -> picking up -> delivering -> idle.
        """
        self._accept_new_orders()
        budget = self.speed
        guard = 0
        while self.orders and guard < 1000:
            guard += 1
            order = self.orders[0]
            if self.state == RiderState.IDLE:
                old = self._set_state(RiderState.PICKING_UP)
                order.mark_picking_up()
                self._waypoints = []
                self._route_target = None
                logger.debug("Rider %s state %s -> %s", self.rider_id, old, self.state)
            target = self._current_target(order)
            if (self.x, self.y) == target:
                self._arrive(order)
                continue
            if budget <= 0:
                break
            budget = self._advance(target, budget)
        if not self.orders and self.state != RiderState.IDLE:
            self._set_state(RiderState.IDLE)

    def reset_route(self):
        """Discard the cached route (used for error recovery)."""
        self._waypoints = []
        self._route_target = None

    def planned_route_points(self):
        """Return the full remaining route through all assigned orders."""
        stops = []
        for i, order in enumerate(self.orders):
            if i == 0 and self.state == RiderState.DELIVERING:
                stops.append(tuple(order.cus_pos))
            else:
                stops.append(tuple(order.res_pos))
                stops.append(tuple(order.cus_pos))
        return PathPlanner.plan_multi((self.x, self.y), stops)

    # ------------------------------------------------------------ persistence
    def to_dict(self):
        """Serialise to a JSON compatible dict."""
        return {
            "rider_id": self.rider_id,
            "x": self.x,
            "y": self.y,
            "speed": self.speed,
            "state": self.state,
            "orders": [o.id for o in self.orders],
            "special_case": self.special_case,
            "delivered_count": self.delivered_count,
            "accepted_ids": sorted(i for i in self._accepted_ids if i is not None),
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
        rider.state = int(data.get("state", RiderState.IDLE))
        rider.special_case = bool(data.get("special_case", False))
        rider.delivered_count = int(data.get("delivered_count", 0))
        rider.log = list(data.get("log", []))
        rider._accepted_ids = set(data.get("accepted_ids", []))
        rider._waypoints = []
        rider._route_target = None
        orders_by_id = orders_by_id or {}
        rider.orders = [orders_by_id[i] for i in data.get("orders", []) if i in orders_by_id]
        return rider

    def __repr__(self):
        return "Rider(id={}, pos=({}, {}), state={}, orders={})".format(
            self.rider_id, self.x, self.y, self.state, [o.id for o in self.orders])
