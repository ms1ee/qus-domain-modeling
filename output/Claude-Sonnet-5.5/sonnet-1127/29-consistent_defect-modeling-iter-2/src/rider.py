"""Rider model."""

import globalvar
from pathplanner import PathPlanner

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
        self._accepted = set()
        self._record("spawn", None)

    def _record(self, event, order_id):
        self.log.append({
            "event": event,
            "order_id": order_id,
            "time": globalvar.get_value("tick", 0),
            "x": self.x,
            "y": self.y,
            "state": self.state,
        })

    def current_order(self):
        """First order not yet completed, or None."""
        for o in self.orders:
            if getattr(o, "status", None) != "completed":
                return o
        return None

    def pending_count(self):
        """Number of uncompleted orders."""
        return sum(1 for o in self.orders
                   if getattr(o, "status", None) != "completed")

    def move(self):
        """Advance one tick."""
        order = self.current_order()
        if order is None:
            self.state = IDLE
            return
        if self.state == IDLE:
            self.state = PICKING_UP
        if order.id not in self._accepted:
            self._accepted.add(order.id)
            self._record("accepted_order", order.id)
        if self.state == PICKING_UP:
            tx, ty = order.res_pos
            self.x, self.y = PathPlanner.next_position(
                self.x, self.y, tx, ty, self.speed)
            if (self.x, self.y) == (tx, ty):
                self.state = DELIVERING
                self._record("arrived_at_merchant", order.id)
        elif self.state == DELIVERING:
            tx, ty = order.cus_pos
            self.x, self.y = PathPlanner.next_position(
                self.x, self.y, tx, ty, self.speed)
            if (self.x, self.y) == (tx, ty):
                order.status = "completed"
                now = globalvar.get_value("tick", 0)
                order.completion_time = now
                order.time_taken = now - order.start_time
                self.state = PICKING_UP if self.current_order() else IDLE
                self._record("delivered_to_customer", order.id)
