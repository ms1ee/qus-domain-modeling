"""Rider model."""
from src import globalvar


class Rider:
    """A delivery rider. state: 0 idle, 1 picking up, 2 delivering."""

    def __init__(self, rider_id):
        self.rider_id = rider_id
        self.x = 400
        self.y = 400
        self.speed = 20
        self.state = 0
        self.orders = []
        self.special_case = False
        self.log = []
        self._current = None
        self._record("spawn", None)

    def _record(self, event, order):
        self.log.append({
            "event": event,
            "order_id": getattr(order, "id", None),
            "time": globalvar.get_value("time", 0) or 0,
            "pos": (self.x, self.y),
        })

    def _pending(self):
        for o in self.orders:
            if o.status != "completed":
                return o
        return None

    def _step(self, target):
        """Move up to speed units toward target, horizontal first."""
        budget = self.speed
        tx, ty = target
        dx = max(-budget, min(budget, tx - self.x))
        self.x += dx
        budget -= abs(dx)
        if budget > 0:
            dy = max(-budget, min(budget, ty - self.y))
            self.y += dy
        return (self.x, self.y) == (tx, ty)

    def move(self):
        """Advance one tick."""
        if self._current is None or self._current.status == "completed":
            self._current = self._pending()
            if self._current is None:
                self.state = 0
                return
            self.state = 1
            self._current.status = "picking_up"
            self._record("accepted_order", self._current)
        order = self._current
        if self.state == 1:
            if self._step(order.res_pos):
                self.state = 2
                self._record("arrived_at_merchant", order)
        elif self.state == 2:
            if self._step(order.cus_pos):
                order.status = "completed"
                order.end_time = globalvar.get_value("time", 0) or 0
                self._record("delivered_to_customer", order)
                self._current = None
                self.state = 0
