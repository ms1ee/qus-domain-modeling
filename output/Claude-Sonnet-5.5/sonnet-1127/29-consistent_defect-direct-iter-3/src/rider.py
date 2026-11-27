"""Rider class."""
import globalvar


def _step(x, y, tx, ty, speed):
    """Move up to speed units toward target, horizontal then vertical."""
    left = speed
    dx = tx - x
    s = min(abs(dx), left)
    x += s if dx > 0 else -s
    left -= s
    dy = ty - y
    s = min(abs(dy), left)
    y += s if dy > 0 else -s
    return x, y


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
        self.log.append({
            "event": event,
            "order_id": order_id,
            "time": globalvar.get_value("time", 0) or 0,
            "x": self.x,
            "y": self.y,
        })

    def current_order(self):
        """First unfinished order or None."""
        for o in self.orders:
            if o.status != "completed":
                return o
        return None

    def pending_count(self):
        """Number of unfinished orders."""
        return sum(1 for o in self.orders if o.status != "completed")

    def move(self):
        """Advance one tick."""
        order = self.current_order()
        if order is None:
            self.state = 0
            return
        if self.state == 0:
            self.state = 1
            order.picked_up = False
            self._record("accepted_order", order.id)
        if self.state == 1:
            tx, ty = order.res_pos
            self.x, self.y = _step(self.x, self.y, tx, ty, self.speed)
            if (self.x, self.y) == (tx, ty):
                self.state = 2
                order.picked_up = True
                self._record("arrived_at_merchant", order.id)
        elif self.state == 2:
            tx, ty = order.cus_pos
            self.x, self.y = _step(self.x, self.y, tx, ty, self.speed)
            if (self.x, self.y) == (tx, ty):
                order.status = "completed"
                order.end_time = globalvar.get_value("time", 0) or 0
                self._record("delivered_to_customer", order.id)
                nxt = self.current_order()
                if nxt is None:
                    self.state = 0
                else:
                    self.state = 1
                    self._record("accepted_order", nxt.id)
