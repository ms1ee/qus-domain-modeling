"""Order management: creation and assignment."""
import globalvar
from order_model import Order
from pathplanner import to_center


def create_order(rx, ry, cx, cy):
    """Create an order from raw coordinates (converted to cell centers)."""
    order = Order((to_center(rx), to_center(ry)),
                  (to_center(cx), to_center(cy)))
    orders = globalvar.get_value("orders")
    if orders is None:
        orders = []
        globalvar.set_value("orders", orders)
    orders.append(order)
    return order


def find_best_rider_for_order(order):
    """Nearest idle rider (Euclidean to restaurant); fallback least loaded."""
    riders = globalvar.get_value("riders") or []
    if not riders:
        return None

    def dist(r):
        return ((r.x - order.res_pos[0]) ** 2 +
                (r.y - order.res_pos[1]) ** 2) ** 0.5

    idle = [r for r in riders if r.state == 0 and not r.orders]
    if idle:
        return min(idle, key=lambda r: (dist(r), r.rider_id))
    return min(riders, key=lambda r: (len(r.orders), dist(r), r.rider_id))


def assign_order(order):
    """Assign order to best rider; returns rider or None."""
    rider = find_best_rider_for_order(order)
    if rider is not None:
        order.assign_to(rider.rider_id)
        rider.orders.append(order)
    return rider
