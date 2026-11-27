"""Rider model."""
import globalvar
from path_planner import PathPlanner

IDLE, PICKING_UP, DELIVERING = 0, 1, 2


class Rider:
    """A delivery rider."""

    def __init__(self, rider_id):
        self.rider_id = rider_id
        self.x = 400
        self.y = 400
        self.speed = 20
        self.state = IDLE
        self.orders = []
        self.special_case = False
        self.log = []
        self.history = []
        self.planner = PathPlanner()
        self._record("spawn", None)

    def _record(self, event, order_id):
        self.log.append({"event": event, "order_id": order_id})
        self.history.append({
            "time": globalvar.get_value("tick", 0), "x": self.x,
            "y": self.y, "state": self.state, "order_id": order_id,
            "event": event})

    def active_order(self):
        """First order not yet completed."""
        for o in self.orders:
            if o.status != "completed":
                return o
        return None

    def active_count(self):
        return sum(1 for o in self.orders if o.status != "completed")

    def move(self):
        """Advance one tick."""
        order = self.active_order()
        if order is None:
            self.state = IDLE
            return
        if self.state == IDLE:
            self.state = PICKING_UP
            order.status = "picking_up"
            self._record("accepted_order", order.id)
        target = order.res_pos if self.state == PICKING_UP else order.cus_pos
        self.special_case = (self.x == target[0] or self.y == target[1])
        self.x, self.y = self.planner.next_position(
            self.x, self.y, target[0], target[1], self.speed)
        if (self.x, self.y) != tuple(target):
            return
        if self.state == PICKING_UP:
            self.state = DELIVERING
            order.status = "delivering"
            self._record("arrived_at_merchant", order.id)
        else:
            order.status = "completed"
            now = globalvar.get_value("tick", 0)
            order.completion_time = now
            order.time_taken = now - order.start_time
            self.state = IDLE
            self._record("delivered_to_customer", order.id)
            nxt = self.active_order()
            if nxt is not None:
                self.state = PICKING_UP
                nxt.status = "picking_up"
                self._record("accepted_order", nxt.id)
