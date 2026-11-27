"""Order management: creation, assignment and completion tracking."""

import logging

import globalvar
from order_model import Order

logger = logging.getLogger(__name__)


def find_best_rider_for_order(order, riders=None):
    """Return the rider that can reach the order's restaurant soonest.

    Closest-rider-first: the cost of each rider is the distance it still
    has to travel for already committed orders plus the distance to the
    restaurant, which naturally balances the load among riders.  Ties are
    broken by number of active orders, then rider id.  Returns None if no
    riders exist.
    """
    if riders is None:
        riders = globalvar.get_value("riders") or []
    best = None
    best_key = None
    for rider in riders:
        try:
            cost = rider.estimated_cost_to(order.res_pos)
        except Exception as exc:  # pragma: no cover - defensive
            logger.warning("Could not evaluate rider %s: %s",
                           getattr(rider, "rider_id", "?"), exc)
            continue
        active = len([o for o in rider.orders if o.status != "completed"])
        key = (cost, active, rider.rider_id)
        if best_key is None or key < best_key:
            best_key = key
            best = rider
    return best


class OrderManager:
    """Handles order creation, assignment and completion."""

    def create_order(self, coords):
        """Create an order from ``[rx, ry, cx, cy]`` and register it."""
        if len(coords) != 4:
            raise ValueError("Exactly four coordinates are required")
        order = Order((coords[0], coords[1]), (coords[2], coords[3]))
        orders = globalvar.get_value("orders")
        if orders is None:
            orders = []
            globalvar.set_value("orders", orders)
        orders.append(order)
        return order

    def assign(self, order, rider=None):
        """Assign an order to the best (or given) rider; return the rider."""
        if rider is None:
            rider = find_best_rider_for_order(order)
        if rider is None:
            return None
        order.assign_to(rider.rider_id)
        rider.orders.append(order)
        return rider

    def all_orders(self):
        """All orders known to the system."""
        return globalvar.get_value("orders") or []

    def completed_orders(self):
        """Orders that have been delivered."""
        return [o for o in self.all_orders() if o.status == "completed"]

    def settle_completed(self, revenue):
        """Credit revenue for newly completed orders; return amount earned."""
        earned = 0
        for o in self.all_orders():
            if o.status == "completed" and not o.paid:
                o.paid = True
                earned += revenue
        return earned
