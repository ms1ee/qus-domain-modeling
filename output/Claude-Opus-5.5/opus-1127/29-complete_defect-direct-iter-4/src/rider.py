"""Rider model: movement, state and order handling."""

import globalvar
from path_planner import PathPlanner

STATE_IDLE = 0
STATE_PICKING_UP = 1
STATE_DELIVERING = 2
STATE_NAMES = {0: "idle", 1: "picking up", 2: "delivering"}


class Rider:
    """A delivery rider.

    Orders are assigned by appending them to ``rider.orders``; ``move()``
    advances the rider one tick and performs state transitions.
    """

    def __init__(self, rider_id, x=None, y=None, speed=None):
        cfg = globalvar.get_value("config") or {}
        self.rider_id = rider_id
        self.x = int(x if x is not None else cfg.get("spawn_x", 400))
        self.y = int(y if y is not None else cfg.get("spawn_y", 400))
        self.speed = int(speed if speed is not None
                         else cfg.get("rider_speed", 50))
        self.state = STATE_IDLE
        self.orders = []
        self.special_case = False
        self.path = []
        self.route = []
        self.current_order = None
        self.total_distance = 0
        self._order_distance = 0
        self.log = []
        self._log("spawn", None)

    # ------------------------------------------------------------------
    def _log(self, event, order_id):
        self.log.append({
            "event": event,
            "order_id": order_id,
            "time": globalvar.get_value("time", 0),
            "x": self.x,
            "y": self.y,
            "state": self.state,
        })

    def state_name(self):
        """Human-readable state."""
        return STATE_NAMES.get(self.state, "unknown")

    def _plan_to(self, target):
        start = (self.x, self.y)
        self.special_case = PathPlanner.is_special(start, target)
        full = PathPlanner.plan(start, target)
        self.route = full
        self.path = list(full[1:])

    def remaining_distance(self):
        """Distance left on the current planned path."""
        pts = [(self.x, self.y)] + list(self.path)
        return PathPlanner.path_length(pts)

    def _advance(self):
        budget = self.speed
        while budget > 0 and self.path:
            nx, ny = self.path[0]
            dx, dy = nx - self.x, ny - self.y
            d = abs(dx) + abs(dy)
            if d <= budget:
                self.x, self.y = nx, ny
                budget -= d
                moved = d
                self.path.pop(0)
            else:
                moved = budget
                if dx != 0:
                    step = min(budget, abs(dx))
                    self.x += step if dx > 0 else -step
                    budget -= step
                if budget > 0 and dy != 0:
                    step = min(budget, abs(dy))
                    self.y += step if dy > 0 else -step
                    budget -= step
                budget = 0
            self.total_distance += moved
            self._order_distance += moved

    def move(self):
        """Advance one tick: pick up new orders, move, and transition."""
        if self.state == STATE_IDLE:
            self.orders[:] = [o for o in self.orders
                              if getattr(o, "status", None) != "completed"]
            if not self.orders:
                self.special_case = False
                return
            order = self.orders[0]
            self.current_order = order
            if getattr(order, "rider_id", None) is None:
                order.assign_to(self.rider_id)
            order.status = "picking_up"
            order.accept_time = globalvar.get_value("time", 0)
            self.state = STATE_PICKING_UP
            self._order_distance = 0
            self._log("accepted_order", order.id)
            self._plan_to(order.res_pos)

        if self.current_order is None:
            # Inconsistent state: recover to idle.
            self.state = STATE_IDLE
            self.path = []
            return

        self._advance()

        if not self.path:
            order = self.current_order
            if self.state == STATE_PICKING_UP:
                self.state = STATE_DELIVERING
                order.status = "delivering"
                order.pickup_time = globalvar.get_value("time", 0)
                self._log("arrived_at_merchant", order.id)
                self._plan_to(order.cus_pos)
            elif self.state == STATE_DELIVERING:
                order.complete(self._order_distance)
                if order in self.orders:
                    self.orders.remove(order)
                money = globalvar.get_value("money", 0) or 0
                globalvar.set_value("money", money + getattr(order, "fee", 0))
                self.state = STATE_IDLE
                self.current_order = None
                self.path = []
                self.special_case = False
                self._log("delivered_to_customer", order.id)

    # ------------------------------------------------------------------
    def to_dict(self):
        """Serialise to a JSON compatible dict (orders as ids)."""
        return {
            "rider_id": self.rider_id, "x": self.x, "y": self.y,
            "speed": self.speed, "state": self.state,
            "orders": [o.id for o in self.orders],
            "special_case": self.special_case,
            "path": [list(p) for p in self.path],
            "route": [list(p) for p in self.route],
            "current_order": (self.current_order.id
                              if self.current_order else None),
            "total_distance": self.total_distance,
            "order_distance": self._order_distance,
            "log": list(self.log),
        }

    @classmethod
    def from_dict(cls, d, order_map):
        """Rebuild a rider; ``order_map`` maps order id -> Order."""
        r = cls.__new__(cls)
        r.rider_id = d["rider_id"]
        r.x, r.y = int(d["x"]), int(d["y"])
        r.speed = int(d["speed"])
        r.state = int(d["state"])
        r.orders = [order_map[i] for i in d.get("orders", [])
                    if i in order_map]
        r.special_case = bool(d.get("special_case", False))
        r.path = [tuple(p) for p in d.get("path", [])]
        r.route = [tuple(p) for p in d.get("route", [])]
        cid = d.get("current_order")
        r.current_order = order_map.get(cid) if cid is not None else None
        r.total_distance = d.get("total_distance", 0)
        r._order_distance = d.get("order_distance", 0)
        r.log = list(d.get("log", []))
        return r

    def __repr__(self):
        return "Rider(id=%s, pos=(%s,%s), state=%s, orders=%s)" % (
            self.rider_id, self.x, self.y, self.state,
            [o.id for o in self.orders])
