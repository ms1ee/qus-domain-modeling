"""Order management."""
import math
import globalvar


def find_best_rider_for_order(order):
    """Return nearest rider (idle preferred), or None."""
    riders = globalvar.get_value("riders", [])
    if not riders:
        return None
    rx, ry = order.res_pos

    def key(r):
        d = math.hypot(r.x - rx, r.y - ry)
        return (0 if (r.state == 0 and not r.orders) else 1,
                len(r.orders), d, r.rider_id)
    # distance first among idle riders; load balance otherwise
    idle = [r for r in riders if r.state == 0 and not r.orders]
    if idle:
        return min(idle, key=lambda r: (math.hypot(r.x - rx, r.y - ry),
                                        r.rider_id))
    return min(riders, key=key)


class OrderManager:
    """Create and dispatch orders."""

    @staticmethod
    def create(coords):
        from order_model import Order
        order = Order((coords[0], coords[1]), (coords[2], coords[3]))
        globalvar.get_value("orders").append(order)
        return order

    @staticmethod
    def dispatch(order):
        """Assign order to best rider. Returns (rider, recruited)."""
        from system import SystemManager
        recruited = SystemManager.recruit_if_needed()
        rider = find_best_rider_for_order(order)
        if rider is not None:
            order.assign_to(rider.rider_id)
            rider.orders.append(order)
        return rider, recruited
