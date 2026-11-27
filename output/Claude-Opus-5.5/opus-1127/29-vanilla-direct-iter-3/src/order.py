"""Order creation, assignment and completion handling."""

import globalvar as gv
from order_model import Order
from path_planner import PathPlanner


def find_best_rider_for_order(order):
    """Return the rider closest (Euclidean) to the order's restaurant.

    Distance: sqrt((rider_x - restaurant_x)^2 + (rider_y - restaurant_y)^2).
    Ties are broken by fewer assigned orders, then by lower id (load
    balancing).  Returns None if there are no riders.
    """
    riders = gv.get_value("riders") or []
    best = None
    best_key = None
    for rider in riders:
        dist = PathPlanner.euclidean((rider.x, rider.y), order.res_pos)
        key = (dist, len(rider.orders), rider.rider_id)
        if best_key is None or key < best_key:
            best_key = key
            best = rider
    return best


class OrderManager:
    """Handles order creation, dispatch and completion bookkeeping."""

    def __init__(self, system_manager):
        self.system = system_manager

    @staticmethod
    def all_orders():
        """Return the global order list (creating it if needed)."""
        orders = gv.get_value("orders")
        if orders is None:
            orders = []
            gv.set_value("orders", orders)
        return orders

    @staticmethod
    def pending_orders():
        """Orders that are not yet assigned to a rider."""
        return [o for o in OrderManager.all_orders() if o.status == "pending"]

    def create_order(self, raw):
        """Create an order from ``[rx, ry, cx, cy]`` raw coordinates."""
        res = PathPlanner.to_grid_center(raw[0], raw[1])
        cus = PathPlanner.to_grid_center(raw[2], raw[3])
        order = Order(res, cus)
        self.all_orders().append(order)
        return order

    @staticmethod
    def assign(order, rider):
        """Assign ``order`` to ``rider``."""
        order.assign_distance = round(
            PathPlanner.euclidean((rider.x, rider.y), order.res_pos), 2)
        rider.orders.append(order)
        order.assign_to(rider.rider_id)

    def dispatch(self, raw):
        """Create an order, recruit if necessary and assign it.

        Returns (order, new_rider_or_None, assigned_rider_or_None).
        """
        order = self.create_order(raw)
        new_rider = self.system.maybe_recruit()
        rider = find_best_rider_for_order(order)
        if rider is not None:
            self.assign(order, rider)
        return order, new_rider, rider

    def assign_pending(self):
        """Try to assign any orders still waiting for a rider."""
        for order in self.pending_orders():
            self.system.maybe_recruit()
            rider = find_best_rider_for_order(order)
            if rider is None:
                break
            self.assign(order, rider)

    @staticmethod
    def completed_orders():
        """Return all completed orders."""
        return [o for o in OrderManager.all_orders() if o.status == "completed"]

    @staticmethod
    def efficiency_stats():
        """Return (completed count, average time taken or None)."""
        done = OrderManager.completed_orders()
        if not done:
            return 0, None
        avg = sum(o.time_taken for o in done) / len(done)
        return len(done), avg
