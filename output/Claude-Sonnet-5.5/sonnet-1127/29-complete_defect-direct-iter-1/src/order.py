"""Order management."""

import globalvar
from order_model import Order
from path_planner import PathPlanner


def find_best_rider_for_order(order):
    """Return the closest rider (ties: lighter load, lower id) or None."""
    riders = globalvar.get_value("riders", []) or []
    best = None
    best_key = None
    for r in riders:
        key = (PathPlanner.distance(r.pos, order.res_pos),
               len(r.orders), r.rider_id)
        if best_key is None or key < best_key:
            best, best_key = r, key
    return best


class OrderManager:
    """Creates and assigns orders."""

    def create_order(self, coords):
        order = Order((coords[0], coords[1]), (coords[2], coords[3]))
        orders = globalvar.get_value("orders")
        if orders is None:
            orders = []
            globalvar.set_value("orders", orders)
        orders.append(order)
        return order

    def assign(self, order):
        """Assign order to best rider; returns rider or None."""
        rider = find_best_rider_for_order(order)
        if rider is None:
            return None
        order.assign_to(rider.rider_id)
        rider.orders.append(order)
        return rider

    def assign_pending(self):
        for o in globalvar.get_value("orders", []) or []:
            if o.status == "pending":
                self.assign(o)
