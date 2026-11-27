"""Rider model."""
import random

import globalvar

IDLE, PICKING, DELIVERING = 0, 1, 2


class Rider:
    """A delivery rider."""

    def __init__(self, rider_id):
        self.rider_id = rider_id
        # start on a road: one coordinate on a grid line, the other not
        self.x = random.randint(0, 8) * 100
        self.y = random.randint(0, 7) * 100 + random.randint(1, 99)
        self.speed = 50
        self.state = IDLE
        self.orders = []
        self.special_case = False
        self.log = []
        self._record("spawn", None)

    def _record(self, event, order_id):
        self.log.append({"event": event, "order_id": order_id,
                         "time": globalvar.get_value("tick", 0) or 0,
                         "x": self.x, "y": self.y})

    def _step_to(self, tx, ty):
        budget = self.speed
        dx = max(-budget, min(budget, tx - self.x))
        self.x += dx
        budget -= abs(dx)
        dy = max(-budget, min(budget, ty - self.y))
        self.y += dy

    def move(self):
        """Advance one tick."""
        if self.state == IDLE:
            if not self.orders:
                return
            self.state = PICKING
            self._record("accepted_order", self.orders[0].id)
        order = self.orders[0] if self.orders else None
        if order is None:
            self.state = IDLE
            return
        if self.state == PICKING:
            tx, ty = order.res_pos
            self._step_to(tx, ty)
            if (self.x, self.y) == (tx, ty):
                self.state = DELIVERING
                self._record("arrived_at_merchant", order.id)
        elif self.state == DELIVERING:
            tx, ty = order.cus_pos
            self._step_to(tx, ty)
            if (self.x, self.y) == (tx, ty):
                now = globalvar.get_value("tick", 0) or 0
                order.status = "completed"
                order.completion_time = now
                order.time_taken = now - order.start_time
                self._record("delivered_to_customer", order.id)
                self.orders.pop(0)
                self.state = IDLE
