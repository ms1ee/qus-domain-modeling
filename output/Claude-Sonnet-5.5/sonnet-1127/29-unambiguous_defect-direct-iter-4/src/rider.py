"""Rider model."""
import globalvar
from path_planner import PathPlanner

IDLE, PICKING, DELIVERING = 0, 1, 2


class Rider:
    """A delivery rider."""

    def __init__(self, rider_id):
        self.rider_id = rider_id
        self.x = 100
        self.y = 50
        self.speed = 50
        self.state = IDLE
        self.orders = []
        self.special_case = False
        self.log = []
        self._log("spawn", None)

    @property
    def pos(self):
        return (self.x, self.y)

    def _log(self, event, order_id):
        self.log.append({
            "time": globalvar.get_value("time", 0),
            "event": event,
            "order_id": order_id,
            "x": self.x,
            "y": self.y,
        })

    def _go(self, target):
        self.x, self.y = PathPlanner.step(self.pos, target, self.speed)
        return self.pos == tuple(target)

    def move(self):
        """Advance one tick."""
        if self.state == IDLE:
            if not self.orders:
                return
            order = self.orders[0]
            self.state = PICKING
            if hasattr(order, "status"):
                order.status = "picking_up"
            self._log("accepted_order", order.id)
        if not self.orders:
            self.state = IDLE
            return
        order = self.orders[0]
        if self.state == PICKING:
            if self._go(order.res_pos):
                self.state = DELIVERING
                order.status = "delivering"
                self._log("arrived_at_merchant", order.id)
        elif self.state == DELIVERING:
            if self._go(order.cus_pos):
                now = globalvar.get_value("time", 0)
                order.status = "completed"
                order.complete_time = now
                order.duration = now - order.start_time
                self._log("delivered_to_customer", order.id)
                self.orders.pop(0)
                self.state = IDLE
