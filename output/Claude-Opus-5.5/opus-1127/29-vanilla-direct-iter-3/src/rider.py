"""Rider model: movement, state machine and order handling."""

import globalvar as gv
from path_planner import PathPlanner

STATE_IDLE = 0
STATE_PICKING_UP = 1
STATE_DELIVERING = 2
STATE_NAMES = {STATE_IDLE: "idle", STATE_PICKING_UP: "picking up",
               STATE_DELIVERING: "delivering"}


class Rider:
    """A delivery rider.

    Orders are assigned by appending them to ``rider.orders``; the rider
    picks them up in FIFO order during :meth:`move`.
    """

    def __init__(self, rider_id):
        cfg = gv.get_value("config") or {}
        self.rider_id = rider_id
        self.x = int(cfg.get("spawn_x", 435))
        self.y = int(cfg.get("spawn_y", 385))
        self.speed = int(cfg.get("rider_speed", 10))
        self.state = STATE_IDLE
        self.orders = []
        self.special_case = False
        self.current_order = None
        self.path = []
        self.log = []
        self.completed_orders = []
        self.distance_travelled = 0
        self._record("spawn", None)

    # ------------------------------------------------------------------
    def _record(self, event, order_id):
        """Append a status-change entry to the rider log."""
        self.log.append({
            "event": event, "order_id": order_id,
            "time": gv.get_value("time", 0), "x": self.x, "y": self.y,
            "state": self.state,
        })

    def _accept_next_order(self):
        """Take the next unfinished order if idle (state 0 -> 1)."""
        if self.current_order is not None:
            return
        for order in self.orders:
            if getattr(order, "status", None) == "completed":
                continue
            self.current_order = order
            if getattr(order, "rider_id", None) != self.rider_id:
                order.assign_to(self.rider_id)
            if hasattr(order, "mark_picking_up"):
                order.mark_picking_up()
            self.state = STATE_PICKING_UP
            self.path = []
            self._record("accepted_order", order.id)
            return

    def current_target(self):
        """Return the current destination or None."""
        if self.current_order is None:
            return None
        if self.state == STATE_PICKING_UP:
            return tuple(self.current_order.res_pos)
        return tuple(self.current_order.cus_pos)

    def _arrive(self):
        """Handle arrival at the current target."""
        order = self.current_order
        self.path = []
        self.special_case = False
        if self.state == STATE_PICKING_UP:
            self.state = STATE_DELIVERING
            order.mark_picked_up()
            self._record("arrived_at_merchant", order.id)
        else:
            order.mark_completed()
            if order in self.orders:
                self.orders.remove(order)
            self.completed_orders.append(order.id)
            self.current_order = None
            self.state = STATE_IDLE
            self._record("delivered_to_customer", order.id)
            self._accept_next_order()

    def move(self):
        """Advance the rider by one tick.

        Moves up to ``speed`` units along the planned axis-aligned path and
        performs any state transitions (with log entries) on the way.
        """
        self.orders = [o for o in self.orders
                       if getattr(o, "status", None) != "completed"
                       or o is self.current_order]
        self._accept_next_order()
        budget = self.speed
        guard = 0
        while self.current_order is not None and guard < 1000:
            guard += 1
            target = self.current_target()
            if (self.x, self.y) == target:
                self._arrive()
                continue
            if budget <= 0:
                break
            if not self.path:
                self.special_case = PathPlanner.is_special_case(
                    (self.x, self.y), target)
                self.path = PathPlanner.plan_path((self.x, self.y), target)
                if not self.path:
                    continue
            wx, wy = self.path[0]
            if (self.x, self.y) == (wx, wy):
                self.path.pop(0)
                continue
            if self.x != wx:
                delta = wx - self.x
                step = min(budget, abs(delta))
                self.x += step if delta > 0 else -step
            else:
                delta = wy - self.y
                step = min(budget, abs(delta))
                self.y += step if delta > 0 else -step
            budget -= step
            self.distance_travelled += step
            if (self.x, self.y) == (wx, wy):
                self.path.pop(0)

    # ------------------------------------------------------------------
    @property
    def state_name(self):
        """Human readable state."""
        return STATE_NAMES.get(self.state, str(self.state))

    def remaining_route(self):
        """Polyline covering all outstanding orders of this rider."""
        dests = []
        for order in self.orders:
            if order.status == "completed":
                continue
            if order is self.current_order and self.state == STATE_DELIVERING:
                dests.append(tuple(order.cus_pos))
            else:
                dests.append(tuple(order.res_pos))
                dests.append(tuple(order.cus_pos))
        return PathPlanner.plan_route((self.x, self.y), dests)

    def to_dict(self):
        """Serialise to a JSON-friendly dict (orders by id)."""
        return {
            "rider_id": self.rider_id, "x": self.x, "y": self.y,
            "speed": self.speed, "state": self.state,
            "orders": [o.id for o in self.orders],
            "current_order": (self.current_order.id
                              if self.current_order else None),
            "special_case": self.special_case, "log": self.log,
            "completed_orders": self.completed_orders,
            "distance_travelled": self.distance_travelled,
        }

    @classmethod
    def from_dict(cls, data, orders_by_id):
        """Rebuild a rider from :meth:`to_dict` output."""
        obj = cls.__new__(cls)
        obj.rider_id = data["rider_id"]
        obj.x = int(data["x"])
        obj.y = int(data["y"])
        obj.speed = int(data.get("speed", 10))
        obj.state = int(data.get("state", 0))
        obj.orders = [orders_by_id[i] for i in data.get("orders", [])
                      if i in orders_by_id]
        cur = data.get("current_order")
        obj.current_order = orders_by_id.get(cur) if cur is not None else None
        obj.special_case = bool(data.get("special_case", False))
        obj.path = []
        obj.log = list(data.get("log", []))
        obj.completed_orders = list(data.get("completed_orders", []))
        obj.distance_travelled = data.get("distance_travelled", 0)
        return obj

    def __repr__(self):
        return "Rider(id=%s, pos=(%d,%d), state=%s, orders=%d)" % (
            self.rider_id, self.x, self.y, self.state_name, len(self.orders))
