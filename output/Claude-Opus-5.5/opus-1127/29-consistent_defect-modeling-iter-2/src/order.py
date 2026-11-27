"""Order management: creation, assignment and queries."""

import logging
import math

import globalvar
from order_model import Order
from rider import recruit_rider

logger = logging.getLogger(__name__)


def find_best_rider_for_order(order):
    """Return the best rider for ``order``.

    Strategy: the rider with the fewest current (uncompleted) orders wins;
    ties are broken by straight-line distance to the restaurant
    (sqrt((rx - x)^2 + (ry - y)^2)) and then by rider id. If no riders
    exist, one is recruited. The order is not appended to the rider.
    """
    riders = globalvar.get_value("riders")
    if riders is None:
        riders = []
        globalvar.set_value("riders", riders)
    if not riders:
        recruit_rider()
        riders = globalvar.get_value("riders")
    rx, ry = order.res_pos

    def key(r):
        return (r.active_order_count, math.hypot(r.x - rx, r.y - ry), r.rider_id)

    return min(riders, key=key)


class OrderManager:
    """Handles order creation, assignment and completion queries."""

    def _orders(self):
        orders = globalvar.get_value("orders")
        if orders is None:
            orders = []
            globalvar.set_value("orders", orders)
        return orders

    @property
    def orders(self):
        return self._orders()

    def create_order(self, coords):
        """Create an order from [rx, ry, cx, cy] and register it."""
        if len(coords) != 4:
            raise ValueError("exactly four coordinates are required")
        order = Order((coords[0], coords[1]), (coords[2], coords[3]))
        self._orders().append(order)
        return order

    def assign_order(self, order):
        """Assign ``order`` to the best rider and return that rider."""
        rider = find_best_rider_for_order(order)
        order.assign_to(rider.rider_id)
        rider.orders.append(order)
        logger.info("Order %s assigned to rider %s", order.id, rider.rider_id)
        return rider

    def pending_orders(self):
        return [o for o in self._orders() if o.status != "completed"]

    def completed_orders(self):
        return [o for o in self._orders() if o.status == "completed"]

    def get(self, order_id):
        for o in self._orders():
            if o.id == order_id:
                return o
        return None
