"""Order assignment."""
import globalvar
import system
from order_model import Order


def _cost(rider, order):
    dist = abs(rider.x - order.res_pos[0]) + abs(rider.y - order.res_pos[1])
    return dist + 400 * len(rider.orders), rider.rider_id


def find_best_rider_for_order(order):
    """Pick nearest, least loaded rider; recruit one if none exists."""
    riders = globalvar.get_value("riders")
    idle = [r for r in riders if not r.orders]
    if not idle:
        new = system.recruit_rider()
        if new is not None:
            return new
    if not riders:
        return None
    return min(riders, key=lambda r: _cost(r, order))


class OrderManager:
    """Order creation and dispatch."""

    @staticmethod
    def create(coords):
        """Create and assign order. Returns (order, rider, new_rider_added)."""
        before = len(globalvar.get_value("riders"))
        order = Order((coords[0], coords[1]), (coords[2], coords[3]))
        globalvar.get_value("orders").append(order)
        rider = find_best_rider_for_order(order)
        added = len(globalvar.get_value("riders")) > before
        if rider is not None:
            rider.orders.append(order)
            order.assign_to(rider.rider_id)
        return order, rider, added
