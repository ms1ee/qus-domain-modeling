"""Rider model: movement, state machine and status log."""

import logging
from enum import IntEnum

try:
    from . import config, globalvar
    from .path_planner import PathPlanner
    from .order_model import Order
except ImportError:  # pragma: no cover
    import config
    import globalvar
    from path_planner import PathPlanner
    from order_model import Order

logger = logging.getLogger(__name__)


class RiderState(IntEnum):
    """Rider status enumeration."""
    IDLE = 0
    PICKING_UP = 1
    DELIVERING = 2


STATE_NAMES = {
    RiderState.IDLE: "idle",
    RiderState.PICKING_UP: "picking up",
    RiderState.DELIVERING: "delivering",
}

_planner = PathPlanner()


class Rider:
    """A delivery rider moving on the grid map."""

    def __init__(self, rider_id, x=None, y=None, speed=None):
        cfg = globalvar.get_value("config") or {}
        self.rider_id = rider_id
        self.x = int(x if x is not None
                     else cfg.get("rider_start_x", config.RIDER_START_X))
        self.y = int(y if y is not None
                     else cfg.get("rider_start_y", config.RIDER_START_Y))
        self.speed = int(speed if speed is not None
                         else cfg.get("rider_speed", config.RIDER_SPEED))
        self.state = RiderState.IDLE
        self.orders = []
        self.special_case = False
        self.current_order = None
        self.route = []
        self.ticks = 0
        self.total_distance = 0
        self.log = []
        self._log_event("spawn", None)

    # helpers ---------------------------------------------------------------
    @property
    def position(self):
        return self.x, self.y

    @property
    def state_name(self):
        return STATE_NAMES.get(RiderState(int(self.state)), str(self.state))

    def active_orders(self):
        """Orders that are not yet delivered."""
        return [o for o in self.orders
                if getattr(o, "status", None) != "completed"]

    def completed_orders(self):
        return [o for o in self.orders
                if getattr(o, "status", None) == "completed"]

    def _now(self):
        t = globalvar.get_value("time")
        return t if isinstance(t, int) else self.ticks

    def _log_event(self, event, order):
        entry = {
            "event": event,
            "order_id": getattr(order, "id", None) if order is not None
            else None,
            "time": self._now(),
            "x": self.x,
            "y": self.y,
            "state": int(self.state),
        }
        self.log.append(entry)
        logger.debug("Rider %s: %s", self.rider_id, entry)

    def _normalize_orders(self):
        """Turn raw [rx, ry, cx, cy] entries into Order objects."""
        for i, o in enumerate(self.orders):
            if isinstance(o, (list, tuple)) and len(o) == 4:
                new = Order((o[0], o[1]), (o[2], o[3]))
                new.assign_to(self.rider_id)
                self.orders[i] = new

    def _next_pending_order(self):
        self._normalize_orders()
        for o in self.orders:
            if getattr(o, "status", None) not in ("completed",):
                return o
        return None

    @staticmethod
    def _target_of(order, state):
        p = order.res_pos if state == RiderState.PICKING_UP else order.cus_pos
        return int(p[0]), int(p[1])

    def remaining_stops(self):
        """List of all remaining stops for the queued orders."""
        stops = []
        for o in self.active_orders():
            if o is self.current_order and \
                    self.state == RiderState.DELIVERING:
                stops.append(o.customer)
            else:
                stops.extend([o.restaurant, o.customer])
        return stops

    def _advance(self, target, budget):
        """Move along the route toward ``target`` using ``budget`` units."""
        if not self.route or self.route[-1] != target:
            self.route = _planner.plan_route((self.x, self.y), target)
            self.special_case = _planner.is_vertical_special(
                (self.x, self.y), target)
        moved = 0
        while budget > 0 and self.route:
            wx, wy = self.route[0]
            dist = abs(wx - self.x) + abs(wy - self.y)
            if dist == 0:
                self.route.pop(0)
                continue
            if dist <= budget:
                self.x, self.y = wx, wy
                budget -= dist
                moved += dist
                self.route.pop(0)
            else:
                step = budget
                if self.x != wx:
                    d = min(step, abs(wx - self.x))
                    self.x += d if wx > self.x else -d
                    step -= d
                    moved += d
                if step > 0 and self.y != wy:
                    d = min(step, abs(wy - self.y))
                    self.y += d if wy > self.y else -d
                    moved += d
                budget = 0
        self.total_distance += moved
        if self.current_order is not None:
            try:
                self.current_order.distance += moved
            except (AttributeError, TypeError):
                pass
        return budget

    # main tick -------------------------------------------------------------
    def move(self):
        """Advance the rider by one tick.

        Handles order acceptance, movement and the state transitions
        idle -> picking up -> delivering -> (picking up | idle).
        """
        self.ticks += 1
        budget = self.speed
        guard = 0
        while guard < 50:
            guard += 1
            order = self.current_order
            if order is None or getattr(order, "status", None) == "completed":
                self.current_order = None
                order = self._next_pending_order()
                if order is None:
                    self.state = RiderState.IDLE
                    self.special_case = False
                    self.route = []
                    break
                self.current_order = order
                if getattr(order, "rider_id", None) is None:
                    order.assign_to(self.rider_id)
                if order.status == "delivering":
                    self.state = RiderState.DELIVERING
                else:
                    self.state = RiderState.PICKING_UP
                    order.status = "picking_up"
                    order.accept_time = self._now()
                    self._log_event("accepted_order", order)
                self.route = []
            target = self._target_of(order, self.state)
            if (self.x, self.y) != target:
                if budget <= 0:
                    break
                budget = self._advance(target, budget)
                if (self.x, self.y) != target:
                    break
            # reached the target
            self.route = []
            self.special_case = False
            if self.state == RiderState.PICKING_UP:
                self.state = RiderState.DELIVERING
                order.status = "delivering"
                order.pickup_time = self._now()
                self._log_event("arrived_at_merchant", order)
            else:
                if hasattr(order, "mark_completed"):
                    order.mark_completed(self._now())
                else:
                    order.status = "completed"
                self.state = RiderState.IDLE
                self._log_event("delivered_to_customer", order)
                self.current_order = None
                funds_bonus = globalvar.get_value("delivery_fee", 0) or 0
                if funds_bonus:
                    globalvar.set_value(
                        "funds", (globalvar.get_value("funds", 0) or 0)
                        + funds_bonus)
        return self.x, self.y

    # persistence -----------------------------------------------------------
    def to_dict(self):
        return {
            "rider_id": self.rider_id,
            "x": self.x,
            "y": self.y,
            "speed": self.speed,
            "state": int(self.state),
            "special_case": self.special_case,
            "orders": [getattr(o, "id", None) for o in self.orders],
            "current_order": getattr(self.current_order, "id", None),
            "ticks": self.ticks,
            "total_distance": self.total_distance,
            "log": list(self.log),
        }

    @classmethod
    def from_dict(cls, d, orders_by_id):
        r = cls(d["rider_id"], d["x"], d["y"], d["speed"])
        r.state = RiderState(int(d.get("state", 0)))
        r.special_case = bool(d.get("special_case", False))
        r.orders = [orders_by_id[i] for i in d.get("orders", [])
                    if i in orders_by_id]
        cur = d.get("current_order")
        r.current_order = orders_by_id.get(cur) if cur is not None else None
        r.ticks = d.get("ticks", 0)
        r.total_distance = d.get("total_distance", 0)
        r.log = list(d.get("log", []))
        return r

    def __repr__(self):
        return ("Rider(id=%s, pos=(%d, %d), state=%s, orders=%d)"
                % (self.rider_id, self.x, self.y, self.state_name,
                   len(self.orders)))
