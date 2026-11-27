"""Rider model."""
from . import globalvar
from .pathplanner import PathPlanner


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
        self._log("spawn", None)

    @property
    def pos(self):
        return (self.x, self.y)

    def _log(self, event, order_id):
        self.log.append({"event": event, "order_id": order_id,
                         "time": globalvar.get_value("time", 0) or 0,
                         "x": self.x, "y": self.y})

    def _go(self, target):
        self.x, self.y = PathPlanner.step(self.pos, target, self.speed)

    def move(self):
        """Advance one tick."""
        if self.state == 0:
            if not self.orders:
                return
            self.state = 1
            self._log("accepted_order", self.orders[0].id)
            order = self.orders[0]
            order.status = "picking_up"
            return
        order = self.orders[0]
        if self.state == 1:
            self._go(order.res_pos)
            if self.pos == tuple(order.res_pos):
                self.state = 2
                order.status = "delivering"
                self._log("arrived_at_merchant", order.id)
        elif self.state == 2:
            self._go(order.cus_pos)
            if self.pos == tuple(order.cus_pos):
                self.orders.pop(0)
                order.complete()
                self.state = 0
                self._log("delivered_to_customer", order.id)

    def to_dict(self):
        return {"rider_id": self.rider_id, "x": self.x, "y": self.y,
                "speed": self.speed, "state": self.state,
                "orders": [o.id for o in self.orders],
                "special_case": self.special_case}
