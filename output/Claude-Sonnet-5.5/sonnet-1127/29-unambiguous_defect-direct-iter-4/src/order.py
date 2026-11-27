"""Order management and assignment."""
import globalvar
import system
from path_planner import PathPlanner
from order_model import Order


def find_best_rider_for_order(order):
    """Pick the best rider: idle & nearest first, load balanced."""
    riders = globalvar.get_value("riders")
    if not riders:
        system.recruit_rider()
        riders = globalvar.get_value("riders")
        if not riders:
            return None

    def key(r):
        return (len(r.orders), PathPlanner.distance(r.pos, order.res_pos),
                r.rider_id)
    return min(riders, key=key)


class OrderManager:
    """Create and assign orders."""

    def create_order(self, coords):
        """Returns (order, rider, new_rider_added)."""
        order = Order((coords[0], coords[1]), (coords[2], coords[3]))
        riders = globalvar.get_value("riders")
        added = False
        if not any(r.state == 0 and not r.orders for r in riders):
            if system.recruit_rider():
                added = True
        rider = find_best_rider_for_order(order)
        if rider is None:
            return order, None, added
        rider.orders.append(order)
        order.assign_to(rider.rider_id)
        globalvar.get_value("orders").append(order)
        return order, rider, added
