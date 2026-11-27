"""Rider model."""
import globalvar
from path_planner import PathPlanner


class Rider:
    """A delivery rider. state: 0 idle, 1 picking up, 2 delivering."""

    def __init__(self, rider_id):
        self.rider_id = rider_id
        self.x = 400
        self.y = 400
        self.speed = 10
        self.state = 0
        self.orders = []
        self.special_case = False
        self.log = []
        self.current = None
        self._record("spawn", None)

    def _record(self, event, order_id):
        self.log.append({"event": event, "order_id": order_id,
                         "time": globalvar.get_value("time", 0),
                         "pos": (self.x, self.y)})

    def pending_orders(self):
        return [o for o in self.orders if o.status != "completed"]

    def _take_next(self):
        for o in self.orders:
            if o.status in ("pending", "assigned"):
                self.current = o
                o.status = "picking"
                self.state = 1
                self._record("accepted_order", o.id)
                return True
        return False

    def move(self):
        """Advance one tick."""
        if self.state == 0:
            if not self._take_next():
                return
        o = self.current
        if o is None:
            self.state = 0
            return
        target = o.res_pos if self.state == 1 else o.cus_pos
        self.x, self.y = PathPlanner.next_step(
            (self.x, self.y), target, self.speed)
        if (self.x, self.y) != tuple(target):
            return
        if self.state == 1:
            self._record("arrived_at_merchant", o.id)
            o.status = "delivering"
            self.state = 2
        else:
            o.status = "completed"
            o.end_time = globalvar.get_value("time", 0)
            self._record("delivered_to_customer", o.id)
            self.current = None
            self.state = 0
            self._take_next()
