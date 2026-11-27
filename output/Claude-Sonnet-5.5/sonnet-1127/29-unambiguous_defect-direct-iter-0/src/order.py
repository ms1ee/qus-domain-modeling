"""Order management and assignment."""
import globalvar
from order_model import Order
from path_planner import PathPlanner


def _cost(rider, order):
    base = PathPlanner.distance(rider.pos, order.res_pos)
    load = len([o for o in rider.orders if o.status != "completed"])
    return base + load * 400 + (0 if rider.state == 0 else 200)


def find_best_rider_for_order(order):
    """Pick best rider (distance + load); recruit if none or all busy."""
    from system import SystemManager
    riders = globalvar.get_value("riders")
    if riders is None:
        riders = []
        globalvar.set_value("riders", riders)
    if not any(r.state == 0 and not r.orders for r in riders):
        SystemManager.recruit_rider()
    if not riders:
        return None
    return min(riders, key=lambda r: (_cost(r, order), r.rider_id))


class OrderManager:
    """Creates and dispatches orders."""

    @staticmethod
    def create_order(coords):
        """Create order from [rx, ry, cx, cy] and dispatch it."""
        before = len(globalvar.get_value("riders", []))
        order = Order((coords[0], coords[1]), (coords[2], coords[3]))
        rider = find_best_rider_for_order(order)
        if rider is None:
            return order, None, False
        order.assign_to(rider.rider_id)
        rider.orders.append(order)
        globalvar.get_value("orders").append(order)
        added = len(globalvar.get_value("riders")) > before
        return order, rider, added
