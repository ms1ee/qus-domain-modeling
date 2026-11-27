"""Rider class."""
import globalvar


class Rider:
    """A delivery rider."""

    def __init__(self, rider_id):
        self.rider_id = rider_id
        self.x = 400
        self.y = 400
        self.speed = 20
        self.state = 0
        self.orders = []
        self.special_case = False
        self.log = []
        self._record("spawn", None)

    def _record(self, event, order_id):
        self.log.append({"event": event, "order_id": order_id,
                         "time": globalvar.get_value("time") or 0,
                         "pos": (self.x, self.y)})

    def current_order(self):
        """First unfinished order."""
        for o in self.orders:
            if o.status != "completed":
                return o
        return None

    def _step_toward(self, tx, ty):
        budget = self.speed
        dx = tx - self.x
        step = min(abs(dx), budget)
        self.x += step if dx > 0 else -step
        budget -= step
        dy = ty - self.y
        step = min(abs(dy), budget)
        self.y += step if dy > 0 else -step

    def move(self):
        """Advance one tick."""
        order = self.current_order()
        if self.state == 0:
            if order is None:
                return
            self.state = 1
            order.status = "picking_up"
            self._record("accepted_order", order.id)
        if order is None:
            self.state = 0
            return
        if self.state == 1:
            tx, ty = order.res_pos
            self._step_toward(tx, ty)
            if (self.x, self.y) == (tx, ty):
                self.state = 2
                order.status = "delivering"
                order.picked = True
                self._record("arrived_at_merchant", order.id)
        elif self.state == 2:
            tx, ty = order.cus_pos
            self._step_toward(tx, ty)
            if (self.x, self.y) == (tx, ty):
                order.status = "completed"
                order.end_time = globalvar.get_value("time") or 0
                self._record("delivered_to_customer", order.id)
                nxt = self.current_order()
                if nxt is not None:
                    self.state = 1
                    nxt.status = "picking_up"
                    self._record("accepted_order", nxt.id)
                else:
                    self.state = 0
