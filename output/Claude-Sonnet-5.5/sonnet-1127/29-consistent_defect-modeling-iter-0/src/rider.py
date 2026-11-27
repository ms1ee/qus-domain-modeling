"""Rider model."""
import globalvar

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

    def _record(self, event, order):
        self.log.append({
            "event": event,
            "order_id": order.id if order is not None else None,
            "time": globalvar.get_value("tick", 0) or 0,
            "x": self.x,
            "y": self.y,
        })

    def current_order(self):
        """First order not yet completed."""
        for o in self.orders:
            if o.status != "completed":
                return o
        return None

    def pending_count(self):
        return sum(1 for o in self.orders if o.status != "completed")

    def move(self):
        """Advance one tick."""
        budget = self.speed
        for _ in range(10):
            order = self.current_order()
            if order is None:
                self.state = IDLE
                return
            if self.state == IDLE:
                self.state = PICKING_UP
                self._record("accepted_order", order)
            target = order.res_pos if self.state == PICKING_UP else order.cus_pos
            if (self.x, self.y) == tuple(target):
                if self.state == PICKING_UP:
                    self.state = DELIVERING
                    self._record("arrived_at_merchant", order)
                    continue
                order.status = "completed"
                order.completion_time = globalvar.get_value("tick", 0) or 0
                self.state = IDLE
                self._record("delivered_to_customer", order)
                return
            if budget <= 0:
                return
            budget -= self._step(target, budget)

    def _step(self, target, budget):
        """Move along streets: horizontal first then vertical."""
        used = 0
        dx = target[0] - self.x
        if dx:
            s = min(abs(dx), budget)
            self.x += s if dx > 0 else -s
            used += s
            budget -= s
        dy = target[1] - self.y
        if dy and budget > 0:
            s = min(abs(dy), budget)
            self.y += s if dy > 0 else -s
            used += s
        return used
