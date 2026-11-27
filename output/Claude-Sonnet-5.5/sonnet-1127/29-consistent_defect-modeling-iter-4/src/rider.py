"""Rider model and movement."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import globalvar  # noqa: E402

IDLE, PICKING_UP, DELIVERING = 0, 1, 2


class Rider:
    """A delivery rider."""

    def __init__(self, rider_id):
        self.rider_id = rider_id
        self.x = 400
        self.y = 400
        self.speed = 20
        self.state = IDLE
        self.orders = []
        self.special_case = False
        self.log = []
        self._record("spawn", None)

    def _record(self, event, order_id):
        self.log.append({"event": event, "order_id": order_id,
                         "time": globalvar.get_value("tick") or 0,
                         "x": self.x, "y": self.y, "state": self.state})

    def current_order(self):
        """First order not yet completed, or None."""
        for o in self.orders:
            if o.status != "completed":
                return o
        return None

    def pending_count(self):
        return sum(1 for o in self.orders if o.status != "completed")

    def _step_toward(self, tx, ty):
        """Move along streets (horizontal first, then vertical)."""
        budget = self.speed
        dx = tx - self.x
        if dx and budget:
            m = min(abs(dx), budget)
            self.x += m if dx > 0 else -m
            budget -= m
        dy = ty - self.y
        if dy and budget:
            m = min(abs(dy), budget)
            self.y += m if dy > 0 else -m
            budget -= m

    def move(self):
        """Advance one tick."""
        order = self.current_order()
        if self.state == IDLE:
            if order is None:
                return
            self.state = PICKING_UP
            order.status = "picking_up"
            self._record("accepted_order", order.id)
        if order is None:
            self.state = IDLE
            return
        if self.state == PICKING_UP:
            tx, ty = order.res_pos
            self._step_toward(tx, ty)
            if (self.x, self.y) == (tx, ty):
                self.state = DELIVERING
                order.status = "delivering"
                self._record("arrived_at_merchant", order.id)
            return
        if self.state == DELIVERING:
            tx, ty = order.cus_pos
            self._step_toward(tx, ty)
            if (self.x, self.y) == (tx, ty):
                order.status = "completed"
                order.completion_time = globalvar.get_value("tick") or 0
                self.state = IDLE
                self._record("delivered_to_customer", order.id)
