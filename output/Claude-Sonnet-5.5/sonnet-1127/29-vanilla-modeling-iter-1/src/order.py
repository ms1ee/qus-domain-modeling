"""Order assignment logic."""

import math

import globalvar
from order_model import Order


def find_best_rider_for_order(order):
    """Return the rider closest (Euclidean) to the restaurant, or None."""
    riders = globalvar.get_value("riders", []) or []
    best = None
    best_key = None
    for r in riders:
        d = math.hypot(r.x - order.res_pos[0], r.y - order.res_pos[1])
        key = (d, len(r.orders))
        if best_key is None or key < best_key:
            best, best_key = r, key
    return best


class OrderManager:
    """Creates and assigns orders."""

    def create_order(self, rx, ry, cx, cy):
        order = Order((rx, ry), (cx, cy))
        orders = globalvar.get_value("orders")
        if orders is None:
            orders = []
            globalvar.set_value("orders", orders)
        orders.append(order)
        return order

    def assign(self, order):
        rider = find_best_rider_for_order(order)
        if rider is None:
            return None
        rider.orders.append(order)
        order.assign_to(rider.rider_id)
        return rider

    def pending_count(self):
        return sum(1 for o in globalvar.get_value("orders", [])
                   if o.status == "pending")
