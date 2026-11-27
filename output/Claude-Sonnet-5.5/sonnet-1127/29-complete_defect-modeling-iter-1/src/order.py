"""Order management and assignment."""
import globalvar
from order_model import Order
from gridmap import GRID


def _dist(rider, order):
    return abs(rider.x - order.res_pos[0]) + abs(rider.y - order.res_pos[1])


def find_best_rider_for_order(order):
    """Closest rider first; idle/less-loaded riders win ties for balance."""
    riders = globalvar.get_value("riders", []) or []
    if not riders:
        return None
    return min(riders, key=lambda r: (_dist(r, order) + 200 * len(r.orders),
                                      len(r.orders), r.rider_id))


class OrderManager:
    """Creates, assigns and completes orders."""

    def create_order(self, coords):
        """Validate coords and create an order."""
        if len(coords) != 4:
            raise ValueError("Need 4 integers: rx ry cx cy")
        for c in coords:
            if not GRID.valid(c):
                raise ValueError("Coordinates must be integers in 0-800")
        order = Order((coords[0], coords[1]), (coords[2], coords[3]))
        orders = globalvar.get_value("orders")
        if orders is None:
            orders = []
            globalvar.set_value("orders", orders)
        orders.append(order)
        return order

    def assign(self, order):
        """Assign order to best rider; returns rider or None."""
        rider = find_best_rider_for_order(order)
        if rider is not None:
            order.assign_to(rider.rider_id)
            rider.orders.append(order)
        return rider

    def assign_pending(self):
        """Try assigning all unassigned orders."""
        for o in globalvar.get_value("orders", []) or []:
            if o.status == "pending":
                self.assign(o)
