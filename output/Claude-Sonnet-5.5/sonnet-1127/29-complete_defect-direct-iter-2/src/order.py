"""Order management."""
import globalvar
from order_model import Order
from path_planner import PathPlanner


def find_best_rider_for_order(order):
    """Return the closest rider (idle riders preferred), or None."""
    riders = globalvar.get_value("riders", [])
    if not riders:
        return None

    def key(r):
        d = PathPlanner.distance((r.x, r.y), order.res_pos)
        return (len(r.orders), d, r.rider_id)
    return min(riders, key=key)


class OrderManager:
    """Create and assign orders."""

    def create_order(self, coords):
        """Create order from [rx, ry, cx, cy], assign it; return (order, rider)."""
        order = Order((coords[0], coords[1]), (coords[2], coords[3]))
        globalvar.get_value("orders").append(order)
        rider = find_best_rider_for_order(order)
        if rider is not None:
            order.assign_to(rider.rider_id)
            rider.orders.append(order)
        return order, rider
