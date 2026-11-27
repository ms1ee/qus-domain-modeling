"""Order management and assignment."""
import globalvar
from order_model import Order
from rider import Rider


def find_best_rider_for_order(order):
    """Rider with fewest active orders, ties broken by distance."""
    riders = globalvar.get_value("riders") or []
    if not riders:
        return None
    rx, ry = order.res_pos

    def key(r):
        d = ((r.x - rx) ** 2 + (r.y - ry) ** 2) ** 0.5
        return (len(r.active_orders()), d, r.rider_id)

    return min(riders, key=key)


def to_grid(v):
    """Convert coordinate to top-left corner of its grid cell."""
    v = max(0, min(800, v))
    return (v // 100) * 100


class OrderManager:
    """Creates, recruits for and assigns orders."""

    def create_order(self, rx, ry, cx, cy):
        """Create an order; returns (order, rider, recruited)."""
        order = Order((to_grid(rx), to_grid(ry)), (to_grid(cx), to_grid(cy)))
        order.start_time = globalvar.get_value("time", 0)
        globalvar.get_value("orders").append(order)
        recruited = self.maybe_recruit()
        rider = find_best_rider_for_order(order)
        if rider is None:
            return order, None, recruited
        order.assign_to(rider.rider_id)
        rider.orders.append(order)
        return order, rider, recruited

    def maybe_recruit(self):
        """Hire a rider if funds and demand allow."""
        riders = globalvar.get_value("riders")
        pending = len([o for o in globalvar.get_value("orders")
                       if o.status in ("pending", "assigned")])
        idle = len([r for r in riders if r.state == 0
                    and not r.active_orders()])
        funds = globalvar.get_value("funds")
        if funds >= 300 and pending > idle:
            rid = globalvar.get_value("rider_id_counter") + 1
            globalvar.set_value("rider_id_counter", rid)
            riders.append(Rider(rid))
            globalvar.set_value("funds", funds - 500)
            return True
        return False
