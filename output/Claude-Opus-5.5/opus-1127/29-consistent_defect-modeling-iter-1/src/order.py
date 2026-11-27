"""Order management: creation, assignment and completion tracking."""

import math

import globalvar
from order_model import Order


def _euclid(rider, order):
    return math.sqrt((rider.x - order.res_x) ** 2 + (rider.y - order.res_y) ** 2)


def find_best_rider_for_order(order):
    """Return the best rider for ``order``.

    Riders with the fewest current (uncompleted) orders are preferred; ties
    are broken by the straight-line distance to the restaurant, then by id.
    If no rider exists, one is recruited.
    """
    riders = globalvar.get_value("riders")
    if not riders:
        from system import create_rider
        return create_rider()
    return min(riders, key=lambda r: (r.active_order_count(),
                                      _euclid(r, order), r.rider_id))


class OrderManager:
    """Handles order creation, assignment and completion queries."""

    def __init__(self, system_manager=None):
        self.assignment_strategy = "fewest-orders-then-closest"
        self.system_manager = system_manager

    @staticmethod
    def all_orders():
        """All orders ever created."""
        orders = globalvar.get_value("orders")
        if orders is None:
            orders = []
            globalvar.set_value("orders", orders)
        return orders

    def create_order(self, res_pos, cus_pos):
        """Create and register an order."""
        order = Order(res_pos, cus_pos)
        self.all_orders().append(order)
        return order

    def pending_orders(self):
        """Orders not yet assigned to a rider."""
        return [o for o in self.all_orders() if o.status == "pending"]

    def completed_orders(self):
        """Completed orders."""
        return [o for o in self.all_orders() if o.status == "completed"]

    def dispatch(self, order):
        """Run recruitment check and assign ``order``.

        Returns ``(rider, new_rider_or_None)``.
        """
        recruited = None
        if self.system_manager is not None:
            recruited = self.system_manager.check_recruitment()
        before = len(globalvar.get_value("riders") or [])
        rider = find_best_rider_for_order(order)
        if recruited is None and len(globalvar.get_value("riders") or []) > before:
            recruited = rider
        order.assign_to(rider.rider_id)
        rider.orders.append(order)
        return rider, recruited
