"""Order assignment logic and OrderManager."""

import math

import globalvar
import system
from order_model import Order


def _distance(rider, order):
    rx, ry = order.res_pos
    return math.sqrt((rider.x - rx) ** 2 + (rider.y - ry) ** 2)


def find_best_rider_for_order(order):
    """Return the best rider: fewest current orders, then closest, then id.

    Recruits a rider if none exist and funds allow. Returns None if no rider
    is available.
    """
    riders = globalvar.get_value("riders")
    if not riders:
        system.recruit_rider()
        riders = globalvar.get_value("riders")
    if not riders:
        return None
    return min(riders, key=lambda r: (len(r.active_orders()),
                                      _distance(r, order), r.rider_id))


class OrderManager:
    """Handles order creation, assignment and completion queries."""

    def create_order(self, coords):
        """Create and assign an order from [rx, ry, cx, cy].

        Returns (order, rider, recruited_flag).
        """
        order = Order(coords[0:2], coords[2:4])
        orders = globalvar.get_value("orders")
        if orders is None:
            orders = []
            globalvar.set_value("orders", orders)
        orders.append(order)
        before = len(globalvar.get_value("riders") or [])
        system.auto_recruit()
        rider = find_best_rider_for_order(order)
        recruited = len(globalvar.get_value("riders") or []) > before
        if rider is not None:
            rider.orders.append(order)
            order.assign_to(rider.rider_id)
        return order, rider, recruited

    @staticmethod
    def completed_orders():
        """List of completed orders."""
        return [o for o in globalvar.get_value("orders") or []
                if o.status == "completed"]
