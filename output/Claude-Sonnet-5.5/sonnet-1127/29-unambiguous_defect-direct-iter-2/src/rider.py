"""Rider model."""
import globalvar
from path_planner import PathPlanner


class Rider:
    """A delivery rider."""

    def __init__(self, rider_id):
        self.rider_id = rider_id
        self.x = 0
        self.y = 50 + 100 * (rider_id % 8) if rider_id % 8 != 7 else 50
        self.x = 0
        self.speed = 50
        self.state = 0
        self.orders = []
        self.special_case = False
        self.log = []
        self._log("spawn", None)

    def _log(self, event, order_id):
        self.log.append({"event": event, "order_id": order_id,
                         "time": globalvar.get_value("time", 0),
                         "pos": (self.x, self.y)})

    def _current(self):
        for o in self.orders:
            if o.status != "completed":
                return o
        return None

    def _step_to(self, target):
        nxt = PathPlanner.step((self.x, self.y), target, self.speed)
        self.x, self.y = nxt
        return nxt == tuple(target)

    def move(self):
        """Advance one tick."""
        order = self._current()
        if order is None:
            self.state = 0
            return
        if self.state == 0:
            self.state = 1
            self._log("accepted_order", order.id)
        if self.state == 1:
            if self._step_to(order.res_pos):
                self.state = 2
                self._log("arrived_at_merchant", order.id)
        elif self.state == 2:
            if self._step_to(order.cus_pos):
                order.complete()
                self._log("delivered_to_customer", order.id)
                self.orders.remove(order)
                self.state = 0

    def to_dict(self):
        """Serialise."""
        return {"rider_id": self.rider_id, "x": self.x, "y": self.y,
                "speed": self.speed, "state": self.state,
                "orders": [o.id for o in self.orders],
                "special_case": self.special_case}
