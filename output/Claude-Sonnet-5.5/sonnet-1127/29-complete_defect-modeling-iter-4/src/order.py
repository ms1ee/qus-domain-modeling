"""Order assignment and management."""

try:
    from src import globalvar
    from src.order_model import Order
except ImportError:  # pragma: no cover
    import globalvar
    from order_model import Order


def find_best_rider_for_order(order):
    """Return the closest rider (ties: fewer orders, lower id) or None."""
    riders = globalvar.get_value("riders", []) or []
    best, best_key = None, None
    for r in riders:
        d = abs(r.x - order.res_pos[0]) + abs(r.y - order.res_pos[1])
        key = (d, len(r.orders), r.rider_id)
        if best_key is None or key < best_key:
            best, best_key = r, key
    return best


class OrderManager:
    """Creates, assigns and records orders."""

    def create_order(self, coords):
        """Create an order from [rx, ry, cx, cy] and register it."""
        order = Order((coords[0], coords[1]), (coords[2], coords[3]))
        orders = globalvar.get_value("orders")
        if orders is None:
            orders = []
            globalvar.set_value("orders", orders)
        orders.append(order)
        return order

    def assign(self, order):
        """Assign to best rider; returns rider or None."""
        rider = find_best_rider_for_order(order)
        if rider is not None:
            order.assign_to(rider.rider_id)
            rider.orders.append(order)
        return rider
