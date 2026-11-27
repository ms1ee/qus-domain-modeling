"""Order creation, assignment and completion handling."""

import math

import globalvar
from order_model import Order
from path_planner import PathPlanner


def _rider_score(rider, order):
    """Sort key: load first (balancing), then distance, then id."""
    active = [o for o in rider.orders if o.status != "completed"]
    ex, ey = rider.expected_free_position()
    rx, ry = order.res_pos
    dist = abs(ex - rx) + abs(ey - ry)
    return (len(active), dist, rider.rider_id)


def find_best_rider_for_order(order):
    """Return the best rider for ``order`` (closest available first).

    Idle riders (no active orders) are preferred; among riders with equal
    load the one closest to the restaurant wins.  Returns None when there
    are no riders.
    """
    riders = globalvar.get_value("riders") or []
    if not riders:
        return None
    return min(riders, key=lambda r: _rider_score(r, order))


class OrderManager:
    """Handles order creation, dispatching and reporting."""

    def __init__(self, system_manager=None):
        self.system = system_manager
        self.planner = PathPlanner()

    @staticmethod
    def orders():
        """All orders known to the system."""
        lst = globalvar.get_value("orders")
        if lst is None:
            lst = []
            globalvar.set_value("orders", lst)
        return lst

    def create_order(self, rx, ry, cx, cy):
        """Create and register an order from raw coordinates."""
        order = Order((rx, ry), (cx, cy))
        self.orders().append(order)
        return order

    def dispatch(self, order):
        """Assign ``order`` to the best rider, recruiting first if possible.

        :return: tuple ``(rider or None, recruited: bool)``.
        """
        recruited = False
        if self.system is not None:
            recruited = self.system.check_recruitment() is not None
        rider = find_best_rider_for_order(order)
        if rider is None:
            return None, recruited
        order.assign_to(rider.rider_id)
        rider.orders.append(order)
        return rider, recruited

    def assign_pending(self):
        """Try to assign all pending orders; returns number assigned."""
        count = 0
        for order in self.orders():
            if order.status == "pending" and order.rider_id is None:
                rider = find_best_rider_for_order(order)
                if rider is None:
                    break
                order.assign_to(rider.rider_id)
                rider.orders.append(order)
                count += 1
        return count

    def planned_route(self, rider, order):
        """Planned route for ``rider`` to fulfil ``order``.

        :return: tuple ``(route_points, distance, eta_ticks)``.
        """
        start = rider.expected_free_position(exclude=order)
        route = self.planner.plan_route([start, order.res_pos, order.cus_pos])
        dist = self.planner.path_length(route)
        eta = math.ceil(dist / rider.speed) if rider.speed else 0
        return route, dist, eta

    def completed_orders(self):
        """List of completed orders."""
        return [o for o in self.orders() if o.status == "completed"]
