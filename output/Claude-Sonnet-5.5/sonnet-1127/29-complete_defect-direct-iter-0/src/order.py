"""Order management and assignment."""
from . import globalvar
from .order_model import Order
from .pathplanner import PathPlanner


def _cost(rider, order):
    load = len(rider.orders)
    dist = PathPlanner.distance(rider.pos, order.res_pos)
    return (0 if rider.state == 0 and load == 0 else 1, dist, load,
            rider.rider_id)


def find_best_rider_for_order(order):
    """Return the closest (preferably idle) rider, or None."""
    riders = globalvar.get_value("riders") or []
    if not riders:
        return None
    return min(riders, key=lambda r: _cost(r, order))


class OrderManager:
    """Creates, assigns and records orders."""

    @staticmethod
    def create(res_pos, cus_pos):
        """Create an order; returns (order, rider, new_rider_added)."""
        from .system import SystemManager
        order = Order(res_pos, cus_pos)
        globalvar.get_value("orders").append(order)
        added = False
        riders = globalvar.get_value("riders")
        if not riders or all(r.state != 0 or r.orders for r in riders):
            added = bool(SystemManager.recruit())
        rider = find_best_rider_for_order(order)
        if rider is not None:
            order.assign_to(rider.rider_id)
            rider.orders.append(order)
        return order, rider, added
