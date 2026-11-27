"""Rider model and movement."""
import globalvar


class Rider:
    """A delivery rider."""

    def __init__(self, rider_id):
        self.rider_id = rider_id
        self.x = 435
        self.y = 385
        self.speed = 10
        self.state = 0
        self.orders = []
        self.special_case = False
        self.log = []
        self._log("spawn", None)

    def _log(self, event, order_id):
        self.log.append({"event": event, "order_id": order_id,
                         "time": globalvar.get_value("tick", 0),
                         "x": self.x, "y": self.y})

    def _step_to(self, tx, ty):
        """Move up to speed units toward target; horizontal first."""
        budget = self.speed
        dx = tx - self.x
        step = min(abs(dx), budget)
        self.x += step if dx > 0 else -step
        budget -= step
        dy = ty - self.y
        step = min(abs(dy), budget)
        self.y += step if dy > 0 else -step
        return self.x == tx and self.y == ty

    def move(self):
        """Advance one tick."""
        if self.state == 0:
            if not self.orders:
                return
            self.state = 1
            self._log("accepted_order", self.orders[0].id)
        order = self.orders[0]
        if self.state == 1:
            if self._step_to(*order.res_pos):
                self.state = 2
                self._log("arrived_at_merchant", order.id)
        elif self.state == 2:
            if self._step_to(*order.cus_pos):
                order.status = "completed"
                order.completion_time = globalvar.get_value("tick", 0)
                self.orders.pop(0)
                self.state = 0
                self._log("delivered_to_customer", order.id)
