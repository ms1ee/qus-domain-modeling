"""Order creation, assignment and completion handling."""

import logging

import globalvar
from order_model import Order
from path_planner import PathPlanner
from system import SystemManager

logger = logging.getLogger(__name__)


def _distance(rider, pos):
    return PathPlanner.euclidean((rider.x, rider.y), pos)


def find_best_rider_for_order(order):
    """Return the best rider for ``order``.

    Closest idle rider (Euclidean distance to the restaurant) first.  If
    pending orders exceed idle riders and funds allow, a new rider is recruited
    automatically.  If no rider is idle, the least loaded (then closest) rider
    is chosen.  Returns None only if there are no riders at all.
    """
    riders = SystemManager.riders()
    pending = [o for o in SystemManager.orders() if o.status == "pending"]
    pending_count = len(pending)
    if order not in pending and getattr(order, "status", "pending") == "pending":
        pending_count += 1
    pending_count = max(pending_count, 1)
    idle = [r for r in riders if r.is_idle()]
    if pending_count > len(idle) and SystemManager.can_recruit():
        new_rider = SystemManager.recruit_rider()
        if new_rider is not None:
            order.new_rider_added = True
            idle.append(new_rider)
    if idle:
        return min(idle, key=lambda r: (_distance(r, order.res_pos), r.rider_id))
    if not riders:
        return None
    return min(riders, key=lambda r: (len(r.orders), _distance(r, order.res_pos),
                                      r.rider_id))


class OrderManager:
    """Handles order creation, assignment and completion queries."""

    @staticmethod
    def create_order(rx, ry, cx, cy):
        """Create and assign an order.

        Returns (order, rider_or_None, new_rider_added).
        """
        order = Order((rx, ry), (cx, cy))
        SystemManager.orders().append(order)
        rider = OrderManager.assign_order(order)
        return order, rider, order.new_rider_added

    @staticmethod
    def assign_order(order):
        """Assign ``order`` to the best rider; returns the rider or None."""
        rider = find_best_rider_for_order(order)
        if rider is None:
            logger.info("Order %s left pending: no rider available", order.id)
            return None
        order.assign_to(rider.rider_id)
        rider.orders.append(order)
        return rider

    @staticmethod
    def assign_pending():
        """Try to assign every pending order."""
        for order in list(SystemManager.pending_orders()):
            if OrderManager.assign_order(order) is None:
                break

    @staticmethod
    def completed_orders():
        """All completed orders."""
        return [o for o in SystemManager.orders() if o.status == "completed"]

    @staticmethod
    def active_orders():
        """All orders not yet completed."""
        return [o for o in SystemManager.orders() if o.status != "completed"]

    @staticmethod
    def get_order(order_id):
        """Find an order by id."""
        for o in SystemManager.orders():
            if o.id == order_id:
                return o
        return None

    @staticmethod
    def rider_by_id(rider_id):
        """Find a rider by id."""
        for r in globalvar.get_value("riders", []) or []:
            if r.rider_id == rider_id:
                return r
        return None
