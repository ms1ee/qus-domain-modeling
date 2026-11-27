"""Rider model."""
import globalvar


class Rider:
    """A delivery rider."""

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

    def _log(self, event, order):
        self.log.append({
            "event": event,
            "order_id": getattr(order, "id", None),
            "time": globalvar.get_value("tick", 0) or 0,
            "x": self.x, "y": self.y, "state": self.state,
        })

    def _step(self, target):
        """Move toward target along x then y; return True if reached."""
        budget = self.speed
        dx = target[0] - self.x
        if dx:
            m = min(budget, abs(dx))
            self.x += m if dx > 0 else -m
            budget -= m
        dy = target[1] - self.y
        if dy and budget:
            m = min(budget, abs(dy))
            self.y += m if dy > 0 else -m
        return (self.x, self.y) == tuple(target)

    def move(self):
        """Advance one tick."""
        if not self.orders:
            self.state = 0
            return
        order = self.orders[0]
        if self.state == 0:
            self.state = 1
            self._log("accepted_order", order)
            order.status = "picking_up"
            return
        if self.state == 1:
            if self._step(order.res_pos):
                self.state = 2
                order.status = "delivering"
                self._log("arrived_at_merchant", order)
        elif self.state == 2:
            if self._step(order.cus_pos):
                self._log("delivered_to_customer", order)
                order.complete(globalvar.get_value("tick", 0) or 0)
                self.orders.pop(0)
                self.state = 0
