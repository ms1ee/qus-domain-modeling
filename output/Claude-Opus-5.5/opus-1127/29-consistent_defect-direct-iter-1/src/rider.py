"""Rider model: movement, state transitions and event log."""

import globalvar
from path_planner import PathPlanner

IDLE = 0
PICKING_UP = 1
DELIVERING = 2

STATE_NAMES = {IDLE: "idle", PICKING_UP: "picking up", DELIVERING: "delivering"}


class Rider:
    """A delivery rider.

    Orders are assigned by appending them to ``rider.orders``; completed
    orders stay in the list as history. Each call to :meth:`move` advances
    the rider by one tick.
    """

    DEFAULT_X = 400
    DEFAULT_Y = 400
    DEFAULT_SPEED = 20

    def __init__(self, rider_id, x=DEFAULT_X, y=DEFAULT_Y, speed=DEFAULT_SPEED):
        self.rider_id = rider_id
        self.x = int(x)
        self.y = int(y)
        self.speed = int(speed)
        self.state = IDLE
        self.orders = []
        self.special_case = False
        self.current_order = None
        self.log = []
        self._log("spawn", None)

    # ------------------------------------------------------------------
    def _log(self, event, order_id):
        self.log.append({
            "event": event,
            "order_id": order_id,
            "time": globalvar.get_value("time", 0) or 0,
            "x": self.x,
            "y": self.y,
            "state": self.state,
        })

    def active_orders(self):
        """Orders that are not completed yet."""
        return [o for o in self.orders if getattr(o, "status", None) != "completed"]

    def _next_order(self):
        if self.current_order is not None and self.current_order in self.orders \
                and self.current_order.status != "completed":
            return self.current_order
        active = self.active_orders()
        return active[0] if active else None

    @property
    def position(self):
        return (self.x, self.y)

    def _advance(self, target, budget):
        """Move toward ``target`` along streets using up to ``budget`` units."""
        points, special = PathPlanner.plan((self.x, self.y), target)
        self.special_case = special
        for wp in points[1:]:
            if budget <= 0:
                break
            dist = PathPlanner.manhattan((self.x, self.y), wp)
            if dist <= budget:
                self.x, self.y = wp
                budget -= dist
            else:
                dx = wp[0] - self.x
                dy = wp[1] - self.y
                if dx != 0:
                    self.x += budget if dx > 0 else -budget
                else:
                    self.y += budget if dy > 0 else -budget
                budget = 0
        return budget

    def move(self):
        """Advance one tick, handling state transitions and logging."""
        budget = self.speed
        for _ in range(4 * max(1, len(self.orders)) + 4):
            order = self._next_order()
            if order is None:
                self.current_order = None
                self.state = IDLE
                self.special_case = False
                break
            if self.current_order is not order:
                self.current_order = order
                if order.status in ("pending", "assigned", None):
                    order.status = "assigned"
                if getattr(order, "rider_id", None) is None:
                    order.rider_id = self.rider_id
                self.state = DELIVERING if order.status == "picked_up" else PICKING_UP
                self._log("accepted_order", order.id)
            target = order.res_pos if self.state == PICKING_UP else order.cus_pos
            target = (int(target[0]), int(target[1]))
            budget = self._advance(target, budget)
            if (self.x, self.y) == target:
                if self.state == PICKING_UP:
                    self.state = DELIVERING
                    order.status = "picked_up"
                    order.picked_time = globalvar.get_value("time", 0) or 0
                    self._log("arrived_at_merchant", order.id)
                else:
                    order.status = "completed"
                    order.completed_time = globalvar.get_value("time", 0) or 0
                    self.current_order = None
                    self.state = PICKING_UP if self.active_orders() else IDLE
                    self._log("delivered_to_customer", order.id)
                    if self.state == IDLE:
                        self.special_case = False
                continue
            if budget <= 0:
                break

    def to_dict(self):
        """Serialize to a JSON compatible dict."""
        return {
            "rider_id": self.rider_id,
            "x": self.x,
            "y": self.y,
            "speed": self.speed,
            "state": self.state,
            "special_case": self.special_case,
            "orders": [o.id for o in self.orders],
            "log": list(self.log),
        }

    def __repr__(self):
        return "Rider(id=%s, pos=(%d,%d), state=%s, orders=%d)" % (
            self.rider_id, self.x, self.y, STATE_NAMES.get(self.state, self.state),
            len(self.orders))
