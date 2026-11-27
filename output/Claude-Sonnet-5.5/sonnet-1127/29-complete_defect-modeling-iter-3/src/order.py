"""Order assignment."""
import globalvar
from order_model import Order


def find_best_rider_for_order(order):
    """Return the closest rider (idle preferred, then least loaded)."""
    riders = globalvar.get_value("riders")
    if riders is None:
        riders = []
        globalvar.set_value("riders", riders)
    if not riders:
        import system
        system.add_rider()
        riders = globalvar.get_value("riders")

    def key(r):
        d = abs(r.x - order.res_pos[0]) + abs(r.y - order.res_pos[1])
        return (len(r.orders), d, r.rider_id)

    return min(riders, key=key)


def create_and_assign(res, cus):
    """Create an order and assign it. Returns (order, rider)."""
    order = Order(res, cus)
    globalvar.get_value("orders").append(order)
    rider = find_best_rider_for_order(order)
    order.assign_to(rider.rider_id)
    rider.orders.append(order)
    return order, rider
