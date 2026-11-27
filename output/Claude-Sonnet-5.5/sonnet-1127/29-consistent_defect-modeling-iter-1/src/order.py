"""Order management."""
import globalvar
from order_model import Order
from rider import Rider


def find_best_rider_for_order(order):
    """Rider with fewest active orders, ties broken by distance."""
    riders = globalvar.get_value("riders", [])
    if not riders:
        return None
    rx, ry = order.res_pos
    return min(riders, key=lambda r: (
        r.active_count(),
        ((r.x - rx) ** 2 + (r.y - ry) ** 2) ** 0.5))


class OrderManager:
    """Creates, assigns, and tracks orders."""

    def pending_count(self):
        return sum(1 for o in globalvar.get_value("orders", [])
                   if o.status == "pending")

    def idle_riders(self):
        return [r for r in globalvar.get_value("riders", [])
                if r.active_count() == 0]

    def maybe_recruit(self, pending):
        """Recruit a rider if conditions hold. Returns True if added."""
        funds = globalvar.get_value("funds")
        if funds >= 300 and pending > len(self.idle_riders()):
            cid = globalvar.get_value("rider_id_counter") + 1
            globalvar.set_value("rider_id_counter", cid)
            globalvar.set_value("funds", funds - 500)
            globalvar.get_value("riders").append(Rider(cid))
            return True
        return False

    def create_order(self, coords):
        """Create and assign an order. Returns (order, new_rider_added)."""
        order = Order((coords[0], coords[1]), (coords[2], coords[3]))
        globalvar.get_value("orders").append(order)
        added = self.maybe_recruit(self.pending_count())
        rider = find_best_rider_for_order(order)
        if rider is not None:
            order.assign_to(rider.rider_id)
            rider.orders.append(order)
        return order, added
