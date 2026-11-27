"""Rider model."""
import globalvar


class Rider:
    """A delivery rider moving on the grid."""

    def __init__(self, rider_id):
        self.rider_id = rider_id
        self.x = 0
        self.y = 0
        self.speed = 50
        self.state = 0
        self.orders = []
        self.special_case = False
        self.log = []
        self._log("spawn", None)

    def _log(self, event, order_id):
        self.log.append({"time": globalvar.get_value("tick", 0),
                         "x": self.x, "y": self.y, "state": self.state,
                         "event": event, "order_id": order_id})

    def _step_towards(self, tx, ty):
        """Move up to speed units along streets (x first, then y)."""
        budget = self.speed
        dx = tx - self.x
        if dx and budget:
            s = min(abs(dx), budget)
            self.x += s if dx > 0 else -s
            budget -= s
        dy = ty - self.y
        if dy and budget:
            s = min(abs(dy), budget)
            self.y += s if dy > 0 else -s

    def move(self):
        """Advance one tick, handling state transitions."""
        if self.state == 0:
            if not self.orders:
                return
            self.state = 1
            self._log("accepted_order", self.orders[0].id)
        order = self.orders[0] if self.orders else None
        if order is None:
            self.state = 0
            return
        if self.state == 1:
            tx, ty = order.res_pos
            self._step_towards(tx, ty)
            if (self.x, self.y) == (tx, ty):
                self.state = 2
                self._log("arrived_at_merchant", order.id)
                order.status = "picked_up"
        elif self.state == 2:
            tx, ty = order.cus_pos
            self._step_towards(tx, ty)
            if (self.x, self.y) == (tx, ty):
                now = globalvar.get_value("tick", 0)
                order.status = "completed"
                order.completion_time = now
                order.time_taken = now - order.start_time
                self.orders.pop(0)
                self.state = 0
                self._log("delivered_to_customer", order.id)
