"""Order management: creation, assignment, completion."""

import logging

import globalvar
from order_model import Order
from path_planner import PathPlanner

logger = logging.getLogger(__name__)


def find_best_rider_for_order(order):
    """Return the best rider for ``order`` (closest rider first).

    Idle riders are preferred, ordered by street distance to the
    restaurant.  If none is idle, the rider with the fewest queued orders
    (then shortest distance from its queue end) is chosen to balance load.
    Returns None when there are no riders.
    """
    riders = globalvar.get_value("riders") or []
    if not riders:
        return None

    def dist(r, start):
        return PathPlanner.path_length(
            start, PathPlanner.find_path(start, order.res_pos))

    idle = [r for r in riders if r.is_available()]
    if idle:
        return min(idle, key=lambda r: (dist(r, (r.x, r.y)), r.rider_id))
    return min(riders, key=lambda r: (len(r.active_orders()),
                                      dist(r, r.queue_end_position()),
                                      r.rider_id))


class OrderManager:
    """Handles order creation, assignment and completion queries."""

    @staticmethod
    def _orders():
        orders = globalvar.get_value("orders")
        if orders is None:
            orders = []
            globalvar.set_value("orders", orders)
        return orders

    def create_order(self, coords):
        """Create an order from ``[rx, ry, cx, cy]`` and record it."""
        if len(coords) != 4:
            raise ValueError("exactly four coordinates are required")
        vals = []
        for c in coords:
            v = int(c)
            if v < 0 or v > 800:
                raise ValueError("coordinate %d out of range 0-800" % v)
            vals.append(v)
        order = Order((vals[0], vals[1]), (vals[2], vals[3]))
        self._orders().append(order)
        logger.info("Created %r", order)
        return order

    def assign_order(self, order):
        """Assign ``order`` to the best rider; returns rider or None."""
        if order.rider_id is not None or order.status == "completed":
            return None
        rider = find_best_rider_for_order(order)
        if rider is None:
            return None
        order.assign_to(rider.rider_id)
        rider.orders.append(order)
        logger.info("Assigned order %d to rider %s", order.id,
                    rider.rider_id)
        return rider

    def assign_pending(self):
        """Try to assign all pending orders; returns list of (order, rider)."""
        result = []
        for order in self._orders():
            if order.status == "pending" and order.rider_id is None:
                rider = self.assign_order(order)
                if rider is not None:
                    result.append((order, rider))
        return result

    def all_orders(self):
        """All orders."""
        return list(self._orders())

    def completed_orders(self):
        """Delivered orders."""
        return [o for o in self._orders() if o.status == "completed"]

    def pending_orders(self):
        """Orders without a rider."""
        return [o for o in self._orders() if o.status == "pending"]
