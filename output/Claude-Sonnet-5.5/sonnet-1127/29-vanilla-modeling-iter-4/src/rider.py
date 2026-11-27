"""Rider model."""
import globalvar
from path_planner import PathPlanner

IDLE, PICKING, DELIVERING = 0, 1, 2


class Rider:
    """A delivery rider."""

    def __init__(self, rider_id):
        self.rider_id = rider_id
        self.x = 435
        self.y = 385
        self.speed = 10
        self.state = IDLE
        self.orders = []
        self.special_case = False
        self.log = []
        self.planner = PathPlanner()
        self._record("spawn", None)

    def _record(self, event, order_id):
        self.log.append({"event": event, "order_id": order_id,
                         "time": globalvar.get_value("tick", 0) or 0,
                         "x": self.x, "y": self.y})

    def _target(self):
        order = self.orders[0]
        return order.res_pos if self.state == PICKING else order.cus_pos

    def move(self):
        """Advance one tick."""
        if self.state == IDLE:
            if not self.orders:
                return
            self.state = PICKING
            self.orders[0].status = "picking"
            self._record("accepted_order", self.orders[0].id)
        if not self.orders:
            self.state = IDLE
            return
        tx, ty = self._target()
        self.x, self.y = self.planner.next_position(
            self.x, self.y, tx, ty, self.speed)
        if (self.x, self.y) != (tx, ty):
            return
        order = self.orders[0]
        if self.state == PICKING:
            self.state = DELIVERING
            order.status = "delivering"
            self._record("arrived_at_merchant", order.id)
        else:
            tick = globalvar.get_value("tick", 0) or 0
            order.complete(tick)
            self._record("delivered_to_customer", order.id)
            self.orders.pop(0)
            self.state = IDLE

    def to_dict(self):
        return {"rider_id": self.rider_id, "x": self.x, "y": self.y,
                "speed": self.speed, "state": self.state,
                "orders": [o.id for o in self.orders],
                "special_case": self.special_case}
