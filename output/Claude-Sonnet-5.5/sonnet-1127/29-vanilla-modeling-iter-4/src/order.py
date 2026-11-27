"""Order management and assignment."""
import math

import globalvar
from order_model import Order


def find_best_rider_for_order(order):
    """Return the rider closest (Euclidean) to the restaurant, or None."""
    riders = globalvar.get_value("riders", []) or []
    best, best_key = None, None
    rx, ry = order.res_pos
    for r in riders:
        d = math.hypot(r.x - rx, r.y - ry)
        key = (d, len(r.orders), r.rider_id)
        if best_key is None or key < best_key:
            best, best_key = r, key
    return best


class OrderManager:
    """Creates, assigns and stores orders."""

    def __init__(self):
        self.orders = []

    def create(self, coords):
        order = Order((coords[0], coords[1]), (coords[2], coords[3]))
        self.orders.append(order)
        globalvar.set_value("orders", self.orders)
        return order

    def assign(self, order):
        rider = find_best_rider_for_order(order)
        if rider is None:
            return None
        order.assign_to(rider.rider_id)
        rider.orders.append(order)
        return rider

    def pending_count(self):
        return sum(1 for o in self.orders if o.status == "pending")

    def unstarted_count(self):
        return sum(1 for o in self.orders if o.status in ("pending", "assigned"))
