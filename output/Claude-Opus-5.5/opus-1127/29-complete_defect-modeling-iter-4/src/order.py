"""Order management: creation, assignment (nearest rider first)."""

import logging

import globalvar
from order_model import Order, ORDER_PENDING, ORDER_COMPLETED
from path_planner import PathPlanner, manhattan
from rider import RiderState

logger = logging.getLogger(__name__)


def find_best_rider_for_order(order):
    """Return the best rider for ``order`` (closest rider first).

    Idle riders without pending orders are preferred and the one closest
    (Manhattan distance) to the restaurant wins.  If every rider is busy,
    the rider with the fewest pending orders whose final position is
    closest is chosen (load balancing).  Returns None if no riders exist.
    """
    riders = globalvar.get_value("riders", []) or []
    if not riders:
        return None
    target = order.res_pos
    idle = [r for r in riders
            if r.state == RiderState.IDLE and not r.has_pending_orders()]
    if idle:
        return min(idle, key=lambda r: (manhattan((r.x, r.y), target),
                                         r.rider_id))
    return min(riders, key=lambda r: (len(r.pending_orders()),
                                      manhattan(r.final_position(), target),
                                      r.rider_id))


class OrderManager:
    """Handles order creation, assignment and pending queue."""

    def __init__(self, planner=None):
        self.assignment_strategy = "nearest"
        self.planner = planner or PathPlanner()

    @staticmethod
    def all_orders():
        orders = globalvar.get_value("orders")
        if orders is None:
            orders = []
            globalvar.set_value("orders", orders)
        return orders

    @staticmethod
    def pending_queue():
        queue = globalvar.get_value("pending_orders")
        if queue is None:
            queue = []
            globalvar.set_value("pending_orders", queue)
        return queue

    def create_order(self, coords):
        """Create an order from ``[rx, ry, cx, cy]`` and register it."""
        if coords is None or len(coords) != 4:
            raise ValueError("an order needs exactly 4 coordinates")
        order = Order(coords[0:2], coords[2:4])
        self.all_orders().append(order)
        fee = globalvar.get_value("order_fee", 100) or 0
        globalvar.set_value("funds", (globalvar.get_value("funds", 0) or 0) + fee)
        return order

    def assign_order(self, order):
        """Assign an order to the best rider, or queue it if none exists.

        :return: (rider or None, preview Route or None)
        """
        rider = find_best_rider_for_order(order)
        if rider is None:
            if order not in self.pending_queue():
                self.pending_queue().append(order)
            return None, None
        start = rider.final_position()
        route = self.planner.plan_multi(start, [order.res_pos, order.cus_pos],
                                        rider.speed)
        rider.orders.append(order)
        order.assign_to(rider.rider_id)
        queue = self.pending_queue()
        if order in queue:
            queue.remove(order)
        return rider, route

    def dispatch_pending(self):
        """Try to assign queued orders. Returns number assigned."""
        assigned = 0
        for order in list(self.pending_queue()):
            if order.status != ORDER_PENDING:
                self.pending_queue().remove(order)
                continue
            rider, _ = self.assign_order(order)
            if rider is None:
                break
            assigned += 1
        return assigned

    def completed_orders(self):
        return [o for o in self.all_orders() if o.status == ORDER_COMPLETED]
