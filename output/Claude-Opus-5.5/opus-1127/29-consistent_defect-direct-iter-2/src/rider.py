"""Rider model: movement, state and order handling."""

import globalvar
from path_planner import PathPlanner

IDLE = 0
PICKING_UP = 1
DELIVERING = 2

STATE_NAMES = {IDLE: "idle", PICKING_UP: "picking up", DELIVERING: "delivering"}


class Rider:
    """A delivery rider.

    Orders are assigned by appending them to ``rider.orders``. Completed
    orders remain in the list as delivery history.
    """

    def __init__(self, rider_id):
        self.rider_id = rider_id
        self.x = 400
        self.y = 400
        self.speed = 20
        self.state = IDLE
        self.orders = []
        self.special_case = False
        self.current_order = None
        self.log = []
        self._log("spawn", None)

    # ------------------------------------------------------------------
    def _now(self):
        t = globalvar.get_value("time")
        return t if t is not None else 0

    def _log(self, event, order_id):
        self.log.append({
            "event": event,
            "order_id": order_id,
            "time": self._now(),
            "x": self.x,
            "y": self.y,
        })

    def active_orders(self):
        """Orders that are not completed yet."""
        return [o for o in self.orders
                if getattr(o, "status", None) != "completed"]

    def _next_pending(self):
        for o in self.orders:
            if getattr(o, "status", None) != "completed" and o is not self.current_order:
                return o
        return None

    def _accept(self, order):
        self.current_order = order
        self.state = PICKING_UP
        if getattr(order, "rider_id", None) is None and hasattr(order, "assign_to"):
            order.assign_to(self.rider_id)
        order.status = "picking_up"
        order.accept_time = self._now()
        self._log("accepted_order", order.id)

    # ------------------------------------------------------------------
    def move(self):
        """Advance the rider by one tick."""
        if self.state == IDLE:
            nxt = self._next_pending()
            if nxt is None:
                return
            self._accept(nxt)

        order = self.current_order
        if order is None:
            self.state = IDLE
            return

        if self.state == PICKING_UP:
            tx, ty = order.res_pos
        else:
            tx, ty = order.cus_pos
        self.special_case = (self.x == tx and self.y != ty)
        self.x, self.y, _ = PathPlanner.step(self.x, self.y, tx, ty, self.speed)

        if (self.x, self.y) != (tx, ty):
            return

        if self.state == PICKING_UP:
            self.state = DELIVERING
            order.status = "delivering"
            order.pickup_time = self._now()
            self._log("arrived_at_merchant", order.id)
        else:
            order.status = "completed"
            order.complete_time = self._now()
            self._log("delivered_to_customer", order.id)
            self.current_order = None
            nxt = self._next_pending()
            if nxt is not None:
                self._accept(nxt)
            else:
                self.state = IDLE

    def to_dict(self):
        """Serialisable representation."""
        return {
            "rider_id": self.rider_id,
            "x": self.x,
            "y": self.y,
            "speed": self.speed,
            "state": self.state,
            "orders": [o.id for o in self.orders],
            "special_case": self.special_case,
            "log": self.log,
        }
