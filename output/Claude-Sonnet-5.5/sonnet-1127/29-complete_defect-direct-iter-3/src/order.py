"""Order management."""
from src import globalvar
from src.order_model import Order
from src.path_planner import PathPlanner


def find_best_rider_for_order(order):
    """Return best rider: idle first, nearest to restaurant, least loaded."""
    riders = globalvar.get_value("riders") or []
    if not riders:
        return None

    def key(r):
        d = PathPlanner.distance((r.x, r.y), order.res_pos)
        return (0 if r.state == 0 and not r.orders else 1, d,
                len(r.orders), r.rider_id)
    return min(riders, key=key)


class OrderManager:
    """Creates, assigns and completes orders."""

    def create_order(self, coords):
        """Create an order from four coordinates."""
        order = Order((coords[0], coords[1]), (coords[2], coords[3]))
        globalvar.get_value("orders").append(order)
        return order

    def assign(self, order):
        """Assign order to the best rider; returns rider or None."""
        rider = find_best_rider_for_order(order)
        if rider is None:
            return None
        order.assign_to(rider.rider_id)
        rider.orders.append(order)
        return rider
