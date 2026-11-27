"""Rider model."""
import globalvar
from path_planner import PathPlanner


class Rider:
    """A delivery rider."""

    def __init__(self, rider_id):
        self.rider_id = rider_id
        self.x = 0
        self.y = 50
        self.speed = 50
        self.state = 0
        self.orders = []
        self.special_case = False
        self.current = None
        self.log = []
        self._log("spawn", None)

    def _log(self, event, order_id):
        self.log.append({
            "event": event, "order_id": order_id,
            "time": globalvar.get_value("time", 0) or 0,
            "pos": (self.x, self.y)})

    @property
    def pos(self):
        return (self.x, self.y)

    def _go(self, target):
        self.x, self.y = PathPlanner.step(self.pos, target, self.speed)
        return self.pos == tuple(target)

    def move(self):
        """Advance one tick."""
        if self.state == 0:
            pending = [o for o in self.orders if o.status != "completed"]
            if not pending:
                return
            self.current = pending[0]
            self.state = 1
            self._log("accepted_order", self.current.id)
            if hasattr(self.current, "status"):
                self.current.status = "picking_up"
            return
        order = self.current
        if order is None:
            self.state = 0
            return
        if self.state == 1:
            if self._go(order.res_pos):
                self.state = 2
                self._log("arrived_at_merchant", order.id)
                order.status = "delivering"
        elif self.state == 2:
            if self._go(order.cus_pos):
                self._log("delivered_to_customer", order.id)
                order.complete(globalvar.get_value("time", 0) or 0)
                if order in self.orders:
                    self.orders.remove(order)
                self.current = None
                self.state = 0
