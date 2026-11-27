"""Rider class."""
import globalvar
from path_planner import PathPlanner

_planner = PathPlanner()


class Rider:
    """A delivery rider. state: 0 idle, 1 picking up, 2 delivering."""

    def __init__(self, rider_id):
        self.rider_id = rider_id
        self.x = 0
        self.y = 0
        self.speed = 50
        self.state = 0
        self.orders = []
        self.special_case = False
        self.log = []
        self._record("spawn", None)

    def _record(self, event, order_id):
        self.log.append({"event": event, "order_id": order_id,
                         "time": globalvar.get_value("tick", 0) or 0,
                         "x": self.x, "y": self.y})

    def move(self):
        """Advance one tick."""
        if self.state == 0 and self.orders:
            self.state = 1
            self.orders[0].status = "picking_up"
            self._record("accepted_order", self.orders[0].id)
        if self.state == 0:
            return
        order = self.orders[0]
        budget = self.speed
        while budget > 0 and self.state != 0:
            target = order.res_pos if self.state == 1 else order.cus_pos
            self.special_case = self.x == target[0] or self.y == target[1]
            nx, ny = _planner.step(self.x, self.y, target[0], target[1],
                                   budget)
            budget -= abs(nx - self.x) + abs(ny - self.y)
            self.x, self.y = nx, ny
            if (self.x, self.y) != tuple(target):
                break
            if self.state == 1:
                self.state = 2
                order.status = "delivering"
                self._record("arrived_at_merchant", order.id)
            else:
                now = globalvar.get_value("tick", 0) or 0
                order.status = "completed"
                order.completion_time = now
                order.time_taken = now - order.start_time
                self._record("delivered_to_customer", order.id)
                self.orders.pop(0)
                self.state = 0
                self.special_case = False
        if self.state == 0 and (self.x, self.y) == tuple(order.cus_pos):
            return

    def to_dict(self):
        return {"rider_id": self.rider_id, "x": self.x, "y": self.y,
                "speed": self.speed, "state": self.state,
                "orders": [o.id for o in self.orders],
                "special_case": self.special_case, "log": self.log}
