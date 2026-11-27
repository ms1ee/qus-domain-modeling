"""Rider model."""
import globalvar

PENDING = ("pending", "assigned")


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
        self.current = None
        self.log = []
        self._log("spawn", None)

    def _log(self, event, order_id):
        self.log.append({"event": event, "order_id": order_id,
                         "time": globalvar.get_value("time", 0),
                         "x": self.x, "y": self.y})

    def active_orders(self):
        """Orders not yet completed."""
        return [o for o in self.orders if o.status != "completed"]

    def _accept_next(self):
        for o in self.orders:
            if o.status in PENDING:
                self.current = o
                o.status = "picking_up"
                self.state = 1
                self._log("accepted_order", o.id)
                return True
        return False

    def _step(self, tx, ty):
        budget = self.speed
        dx = tx - self.x
        m = min(abs(dx), budget)
        self.x += m if dx > 0 else -m
        budget -= m
        dy = ty - self.y
        m = min(abs(dy), budget)
        self.y += m if dy > 0 else -m

    def move(self):
        """Advance one tick."""
        if self.state == 0:
            self._accept_next()
            return
        o = self.current
        if o is None:
            self.state = 0
            return
        if self.state == 1:
            self._step(*o.res_pos)
            if (self.x, self.y) == tuple(o.res_pos):
                self.state = 2
                o.status = "delivering"
                self._log("arrived_at_merchant", o.id)
        else:
            self._step(*o.cus_pos)
            if (self.x, self.y) == tuple(o.cus_pos):
                o.status = "completed"
                o.end_time = globalvar.get_value("time", 0)
                self._log("delivered_to_customer", o.id)
                self.current = None
                self.state = 0
                self._accept_next()

    def to_dict(self):
        return {"rider_id": self.rider_id, "x": self.x, "y": self.y,
                "speed": self.speed, "state": self.state,
                "orders": [o.id for o in self.orders],
                "special_case": self.special_case}
