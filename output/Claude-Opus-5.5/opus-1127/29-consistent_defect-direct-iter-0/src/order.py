"""Order management: creation, assignment and completion queries."""

import logging
import math

import globalvar
from order_model import Order, STATUS_COMPLETED, STATUS_PENDING

logger = logging.getLogger(__name__)


def _restaurant_pos(order):
    if hasattr(order, "res_pos"):
        return order.res_pos
    probe = Order((order[0], order[1]), (order[2], order[3]), order_id=-1)
    return probe.res_pos


def rider_distance(rider, pos):
    """Euclidean distance √[(rx - x)² + (ry - y)²]."""
    return math.sqrt((rider.x - pos[0]) ** 2 + (rider.y - pos[1]) ** 2)


def find_best_rider_for_order(order):
    """Return the best rider for ``order`` (None if there are no riders).

    Riders with the fewest outstanding orders are preferred; ties are broken
    by the distance to the restaurant (closest first), then by rider ID.
    """
    riders = globalvar.get_value("riders") or []
    if not riders:
        return None
    res = _restaurant_pos(order)

    def key(r):
        if hasattr(r, "active_order_count"):
            load = r.active_order_count()
        else:
            load = len(getattr(r, "orders", []))
        return (load, rider_distance(r, res), r.rider_id)

    return min(riders, key=key)


class OrderManager:
    """Handles order creation, assignment and completion bookkeeping."""

    def __init__(self):
        if globalvar.get_value("orders") is None:
            globalvar.set_value("orders", [])

    @property
    def orders(self):
        """All orders known to the system."""
        orders = globalvar.get_value("orders")
        if orders is None:
            orders = []
            globalvar.set_value("orders", orders)
        return orders

    def create_order(self, coords):
        """Create an order from ``[rx, ry, cx, cy]`` and register it."""
        if len(coords) != 4:
            raise ValueError("Exactly four coordinates are required.")
        order = Order((coords[0], coords[1]), (coords[2], coords[3]))
        self.orders.append(order)
        logger.info("Created %r", order)
        return order

    def pending_orders(self):
        """Orders not yet assigned to a rider."""
        return [o for o in self.orders if o.status == STATUS_PENDING]

    def completed_orders(self):
        """Delivered orders."""
        return [o for o in self.orders if o.status == STATUS_COMPLETED]

    def get_order(self, order_id):
        """Return order by ID or None."""
        for o in self.orders:
            if o.id == order_id:
                return o
        return None

    def assign(self, order):
        """Assign ``order`` to the best rider. Returns the rider or None."""
        rider = find_best_rider_for_order(order)
        if rider is None:
            return None
        order.assign_to(rider.rider_id)
        rider.orders.append(order)
        logger.info("Assigned order %s to rider %s", order.id, rider.rider_id)
        return rider

    def assign_pending(self):
        """Assign all pending orders. Returns list of (order, rider)."""
        result = []
        for order in self.pending_orders():
            rider = self.assign(order)
            if rider is None:
                break
            result.append((order, rider))
        return result
