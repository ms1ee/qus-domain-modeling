"""Order management: assignment and creation."""
import globalvar
from order_model import Order
from path_planner import PathPlanner


def _effective_pos(rider):
    if rider.orders:
        return rider.orders[-1].cus_pos
    return (rider.x, rider.y)


def find_best_rider_for_order(order):
    """Return the closest rider (ties broken by lighter load), or None."""
    riders = globalvar.get_value("riders", []) or []
    best, best_key = None, None
    for r in riders:
        key = (PathPlanner.distance(_effective_pos(r), order.res_pos),
               len(r.orders), r.rider_id)
        if best_key is None or key < best_key:
            best, best_key = r, key
    return best


class OrderManager:
    """Creates and assigns orders."""

    @staticmethod
    def create_order(coords):
        """Create an order; returns (order, new_rider_added, rider)."""
        import system
        order = Order((coords[0], coords[1]), (coords[2], coords[3]))
        added = system.SystemManager.auto_recruit() > 0
        rider = find_best_rider_for_order(order)
        orders = globalvar.get_value("orders", [])
        orders.append(order)
        globalvar.set_value("orders", orders)
        if rider is not None:
            order.assign_to(rider.rider_id)
            rider.orders.append(order)
        globalvar.set_value("funds", globalvar.get_value("funds", 0) + 100)
        return order, added, rider
