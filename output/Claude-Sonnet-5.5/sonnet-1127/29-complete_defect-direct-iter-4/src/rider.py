"""Rider model."""
import globalvar
from path_planner import PathPlanner

IDLE, PICKING, DELIVERING = 0, 1, 2


class Rider:
    """A delivery rider."""

    def __init__(self, rider_id):
        self.rider_id = rider_id
        self.x = 50
        self.y = 50
        self.speed = 50
        self.state = IDLE
        self.orders = []
        self.special_case = False
        self.log = []
        self._log("spawn", None)

    def _log(self, event, order_id):
        self.log.append({"event": event, "order_id": order_id,
                         "time": globalvar.get_value("time", 0) or 0,
                         "x": self.x, "y": self.y})

    def move(self):
        """Advance one tick."""
        if self.state == IDLE and self.orders:
            self.state = PICKING
            self._log("accepted_order", self.orders[0].id)
        if self.state == IDLE or not self.orders:
            return
        order = self.orders[0]
        if self.state == PICKING:
            self.x, self.y = PathPlanner.step(
                (self.x, self.y), order.res_pos, self.speed)
            if (self.x, self.y) == tuple(order.res_pos):
                self.state = DELIVERING
                self._log("arrived_at_merchant", order.id)
        elif self.state == DELIVERING:
            self.x, self.y = PathPlanner.step(
                (self.x, self.y), order.cus_pos, self.speed)
            if (self.x, self.y) == tuple(order.cus_pos):
                self._log("delivered_to_customer", order.id)
                order.complete()
                self.orders.pop(0)
                self.state = IDLE

    def to_dict(self):
        return {"rider_id": self.rider_id, "x": self.x, "y": self.y,
                "speed": self.speed, "state": self.state,
                "orders": [o.id for o in self.orders],
                "special_case": self.special_case}
