"""Order management: creation, assignment and completion."""

import logging

import globalvar
from order_model import Order
from path_planner import PathPlanner

logger = logging.getLogger(__name__)


def _rider_key(rider, order):
    active = len(rider.active_orders()) if hasattr(rider, "active_orders") \
        else len(rider.orders)
    dist = PathPlanner.euclidean((rider.x, rider.y), order.res_pos)
    return (active, dist, rider.rider_id)


def find_best_rider_for_order(order):
    """Return the best rider for ``order``.

    Riders with the fewest outstanding orders are preferred; ties are
    broken by the straight-line distance to the restaurant, then by id.
    If no riders exist, one is recruited (if funds allow).
    """
    riders = globalvar.get_value("riders") or []
    if not riders:
        from system import get_system
        manager = get_system()
        if manager.funds >= int(manager.config["recruit_threshold"]):
            manager.recruit_rider()
        riders = globalvar.get_value("riders") or []
        if not riders:
            return None
    return min(riders, key=lambda r: _rider_key(r, order))


class OrderManager:
    """Handle order creation, assignment and completion queries."""

    def __init__(self, system_manager):
        self.system = system_manager

    def create_order(self, rx, ry, cx, cy):
        """Create, register and assign an order.

        Returns ``(order, rider, recruited_riders)``.
        """
        order = Order((rx, ry), (cx, cy))
        self.system.orders.append(order)
        recruited = self.system.auto_recruit()
        rider = self.assign(order)
        return order, rider, recruited

    def assign(self, order):
        """Assign ``order`` to the best rider; return the rider or None."""
        rider = find_best_rider_for_order(order)
        if rider is None:
            logger.warning("No rider available for order %s", order.id)
            return None
        order.assign_to(rider.rider_id)
        rider.orders.append(order)
        return rider

    def assign_pending(self):
        """Try to assign any orders still pending; return assigned count."""
        count = 0
        for order in self.system.orders:
            if order.status == "pending":
                if self.assign(order) is not None:
                    count += 1
        return count

    def completed_orders(self):
        """Return all completed orders."""
        return [o for o in self.system.orders if o.status == "completed"]
