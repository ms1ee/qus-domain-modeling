"""Order management: creation, assignment and bookkeeping."""

import logging
import math

import globalvar
from order_model import Order
from rider import RiderState, _order_positions

logger = logging.getLogger(__name__)


def _distance(rider, pos):
    return math.sqrt((rider.x - pos[0]) ** 2 + (rider.y - pos[1]) ** 2)


def find_best_rider_for_order(order):
    """Return the rider closest (Euclidean) to the order's restaurant.

    Idle riders are preferred; if none are idle, the closest rider overall
    is chosen.  Returns None if no riders exist.
    """
    riders = globalvar.get_value("riders") or []
    if not riders:
        return None
    res_pos, _ = _order_positions(order)
    idle = [r for r in riders if r.state == RiderState.IDLE and not r.orders]
    pool = idle or list(riders)
    best = None
    best_dist = None
    for r in pool:
        d = _distance(r, res_pos)
        if best is None or d < best_dist:
            best, best_dist = r, d
    return best


class OrderManager:
    """Handles order creation, assignment and completion queries."""

    def __init__(self, system=None):
        self.system = system
        if globalvar.get_value("orders") is None:
            globalvar.set_value("orders", [])

    @property
    def orders(self):
        """All orders."""
        orders = globalvar.get_value("orders")
        if orders is None:
            orders = []
            globalvar.set_value("orders", orders)
        return orders

    def create_order(self, coords):
        """Create an order from ``[rx, ry, cx, cy]`` and register it."""
        if len(coords) != 4:
            raise ValueError("Exactly four coordinates are required")
        order = Order((coords[0], coords[1]), (coords[2], coords[3]))
        self.orders.append(order)
        logger.info("Created %r", order)
        return order

    def pending_orders(self):
        """Orders not yet assigned to any rider."""
        return [o for o in self.orders if o.status == "pending"]

    def completed_orders(self):
        """Delivered orders."""
        return [o for o in self.orders if o.status == "completed"]

    def assign_order(self, order):
        """Assign ``order`` to the best rider; return the rider or None."""
        rider = find_best_rider_for_order(order)
        if rider is None:
            return None
        rider.orders.append(order)
        order.assign_to(rider.rider_id)
        logger.info("Order %s assigned to rider %s", order.id, rider.rider_id)
        return rider

    def assign_pending(self):
        """Try to assign every pending order. Returns list of (order, rider)."""
        result = []
        for order in self.pending_orders():
            rider = self.assign_order(order)
            if rider is None:
                break
            result.append((order, rider))
        return result

    def get_order(self, order_id):
        """Return the order with ``order_id`` or None."""
        for o in self.orders:
            if o.id == order_id:
                return o
        return None
