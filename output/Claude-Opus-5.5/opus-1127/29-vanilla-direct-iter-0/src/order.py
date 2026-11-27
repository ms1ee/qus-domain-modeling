"""Order creation, assignment and completion handling."""

import math

import globalvar
from order_model import Order
from path_planner import PathPlanner, to_grid_center


def _euclid(rider, pos):
    return math.sqrt((rider.x - pos[0]) ** 2 + (rider.y - pos[1]) ** 2)


def find_best_rider_for_order(order):
    """Return the rider closest (Euclidean) to the order's restaurant.

    Idle riders are preferred; if none are idle, the least loaded rider
    (ties broken by distance) is chosen.  Returns None if no riders exist.
    """
    riders = globalvar.get_value("riders") or []
    if not riders:
        return None
    res = order.res_pos
    idle = [r for r in riders if r.state == 0 and not r.orders]
    if idle:
        return min(idle, key=lambda r: (_euclid(r, res), r.rider_id))
    return min(riders, key=lambda r: (len(r.orders), _euclid(r, res), r.rider_id))


class OrderManager:
    """Handles order creation, assignment and completion records."""

    @staticmethod
    def convert(coords):
        """Convert raw [rx, ry, cx, cy] to grid-center positions."""
        rx, ry, cx, cy = (to_grid_center(v) for v in coords)
        return (rx, ry), (cx, cy)

    def create_order(self, coords):
        """Create an order from four raw coordinates and queue it."""
        res, cus = self.convert(coords)
        order = Order(res, cus)
        globalvar.get_value("orders").append(order)
        globalvar.get_value("pending_orders").append(order)
        return order

    def assign(self, order, rider):
        """Assign ``order`` to ``rider``."""
        start = rider.position
        # if rider already has orders, its route starts at the last customer
        if rider.orders:
            last = rider.orders[-1]
            start = tuple(last.cus_pos)
        path = PathPlanner.plan_multi(start, [order.res_pos, order.cus_pos])
        order.distance = PathPlanner.path_length(path)
        order.estimated_time = math.ceil(order.distance / max(1, rider.speed))
        rider.orders.append(order)
        order.assign_to(rider.rider_id)
        pending = globalvar.get_value("pending_orders", [])
        if order in pending:
            pending.remove(order)
        return path

    def dispatch_pending(self):
        """Assign all pending orders; returns list of (order, rider, path)."""
        results = []
        for order in list(globalvar.get_value("pending_orders", [])):
            rider = find_best_rider_for_order(order)
            if rider is None:
                break
            path = self.assign(order, rider)
            results.append((order, rider, path))
        return results

    @staticmethod
    def all_orders():
        return globalvar.get_value("orders", [])

    @staticmethod
    def completed_orders():
        return [o for o in globalvar.get_value("orders", []) if o.status == "completed"]
