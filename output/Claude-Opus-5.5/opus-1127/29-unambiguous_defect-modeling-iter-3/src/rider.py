"""Rider model: movement, state transitions and status log."""

import logging

import globalvar
from config import DEFAULTS
from grid_map import CELL_SIZE, clamp
from path_planner import PathPlanner

logger = logging.getLogger(__name__)


class RiderState:
    """Rider state enumeration."""
    IDLE = 0
    PICKING_UP = 1
    DELIVERING = 2
    NAMES = {0: "idle", 1: "picking up", 2: "delivering"}

    @classmethod
    def name(cls, state):
        return cls.NAMES.get(state, "unknown")


def _now():
    return int(globalvar.get_value("tick", 0) or 0)


class Rider:
    """A delivery rider.

    Orders are assigned by appending them to ``rider.orders``; each call to
    :meth:`move` advances the rider by one tick.
    """

    def __init__(self, rider_id, x=None, y=None, speed=None):
        cfg = globalvar.get_value("config") or {}
        self.rider_id = int(rider_id)
        if x is None:
            x = cfg.get("rider_start_x", DEFAULTS["rider_start_x"])
        if y is None:
            y = cfg.get("rider_start_y", DEFAULTS["rider_start_y"])
        x, y = clamp(int(x)), clamp(int(y))
        if x % CELL_SIZE != 0 and y % CELL_SIZE != 0:
            # Snap onto the nearest vertical street.
            x = clamp(int(round(x / CELL_SIZE)) * CELL_SIZE)
        self.x = x
        self.y = y
        if speed is None:
            speed = cfg.get("default_speed", DEFAULTS["default_speed"])
        self.speed = max(1, int(speed))
        self.state = RiderState.IDLE
        self.orders = []
        self.special_case = False
        self.route = []
        self.current_order = None
        self.completed_orders = []
        self.distance_travelled = 0
        self.log = []
        self._planner = PathPlanner()
        self._record("spawn", None)

    # ------------------------------------------------------------------ log
    def _record(self, event, order):
        entry = {
            "time": _now(),
            "event": event,
            "order_id": order.id if order is not None else None,
            "x": self.x,
            "y": self.y,
            "state": self.state,
        }
        self.log.append(entry)
        logger.debug("Rider %d: %s", self.rider_id, entry)

    # -------------------------------------------------------------- helpers
    @property
    def position(self):
        return (self.x, self.y)

    def pending_orders(self):
        """Orders not yet completed."""
        return [o for o in self.orders if getattr(o, "status", "") != "completed"]

    def is_available(self):
        """Idle with no queued work."""
        return self.state == RiderState.IDLE and not self.pending_orders()

    def _next_order(self):
        for o in self.orders:
            if getattr(o, "status", "") != "completed":
                return o
        return None

    def _plan_to(self, target):
        self.special_case = self._planner.is_special_case(self.position, target)
        self.route = self._planner.plan(self.position, target)

    def workload(self, exclude=None):
        """Return (remaining distance, final position) of queued work."""
        total = 0
        pos = self.position
        cur = self.current_order
        if cur is not None and cur is not exclude and self.state != RiderState.IDLE:
            total += self._planner.path_length(self.position, self.route)
            if self.route:
                pos = self.route[-1]
            if self.state == RiderState.PICKING_UP:
                total += cur.distance
                pos = cur.cus_pos
        for o in self.pending_orders():
            if o is cur or o is exclude:
                continue
            total += self._planner.distance(pos, o.res_pos) + o.distance
            pos = o.cus_pos
        return total, pos

    def projected_position(self, exclude=None):
        """Position where the rider will be after finishing queued work."""
        return self.workload(exclude)[1]

    # -------------------------------------------------------- transitions
    def _accept(self, order):
        self.current_order = order
        if getattr(order, "rider_id", None) is None:
            order.assign_to(self.rider_id)
        order.status = "picking_up"
        order.accept_time = _now()
        self.state = RiderState.PICKING_UP
        self._plan_to(order.res_pos)
        self._record("accepted_order", order)

    def _arrive_merchant(self):
        order = self.current_order
        order.status = "delivering"
        order.pickup_time = _now()
        self.state = RiderState.DELIVERING
        self._record("arrived_at_merchant", order)
        self._plan_to(order.cus_pos)

    def _deliver(self):
        order = self.current_order
        order.status = "completed"
        order.completion_time = _now()
        order.time_taken = order.completion_time - order.start_time
        if order in self.orders:
            self.orders.remove(order)
        self.completed_orders.append(order.id)
        self.state = RiderState.IDLE
        self.route = []
        self.special_case = False
        self.current_order = None
        self._record("delivered_to_customer", order)
        cfg = globalvar.get_value("config") or {}
        fee = int(cfg.get("delivery_fee", 0) or 0)
        funds = globalvar.get_value("funds")
        if fee and funds is not None:
            globalvar.set_value("funds", funds + fee)

    def _advance(self, budget):
        while budget > 0 and self.route:
            tx, ty = self.route[0]
            if self.x != tx:
                step = min(budget, abs(tx - self.x))
                self.x += step if tx > self.x else -step
            elif self.y != ty:
                step = min(budget, abs(ty - self.y))
                self.y += step if ty > self.y else -step
            else:
                step = 0
            budget -= step
            self.distance_travelled += step
            if (self.x, self.y) == (tx, ty):
                self.route.pop(0)
        return budget

    def move(self):
        """Advance the rider by one tick. Returns True if the rider acted."""
        if self.state == RiderState.IDLE:
            order = self._next_order()
            if order is None:
                return False
            self._accept(order)
        if self.current_order is None:
            # Inconsistent state: recover to idle.
            self.state = RiderState.IDLE
            self.route = []
            return False
        self._advance(self.speed)
        if not self.route:
            if self.state == RiderState.PICKING_UP:
                self._arrive_merchant()
            elif self.state == RiderState.DELIVERING:
                self._deliver()
        return True

    def to_dict(self):
        """Serialisable representation."""
        return {
            "rider_id": self.rider_id,
            "x": self.x,
            "y": self.y,
            "speed": self.speed,
            "state": int(self.state),
            "orders": [o.id for o in self.orders],
            "special_case": self.special_case,
            "completed_orders": list(self.completed_orders),
            "distance_travelled": self.distance_travelled,
            "log": list(self.log),
        }

    def __repr__(self):
        return "Rider(#%d at (%d,%d) %s, %d orders)" % (
            self.rider_id, self.x, self.y, RiderState.name(self.state),
            len(self.orders))
