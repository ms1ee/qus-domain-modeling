"""Order management: creation, assignment and completion tracking."""

import logging

import globalvar
from order_model import Order
from path_planner import PathPlanner, manhattan
from rider import IDLE

logger = logging.getLogger(__name__)


def find_best_rider_for_order(order):
    """Return the most suitable rider for ``order``.

    Idle riders are preferred; among the candidates the nearest one
    (Manhattan distance to the restaurant) wins, ties are broken by the
    number of assigned orders (load balancing) and then by rider id.
    If no riders exist, one is recruited when funds allow; returns None if
    no rider can be found.
    """
    riders = globalvar.get_value("riders") or []
    if not riders:
        from system import SystemManager
        return SystemManager().recruit_rider()
    res = tuple(order.res_pos)
    candidates = [r for r in riders if r.state == IDLE and not r.orders]
    if not candidates:
        candidates = riders
    return min(candidates, key=lambda r: (manhattan((r.x, r.y), res),
                                          len(r.orders), r.rider_id))


class OrderManager:
    """Handles order creation, assignment and pending order processing."""

    def __init__(self, system=None):
        if system is None:
            from system import SystemManager
            system = SystemManager()
        self.system = system
        self.planner = PathPlanner()

    @property
    def orders(self):
        return globalvar.get_value("orders")

    @property
    def pending(self):
        return globalvar.get_value("pending_orders")

    def assign(self, order, rider):
        """Assign ``order`` to ``rider``."""
        rider.orders.append(order)
        order.assign_to(rider.rider_id)

    def create_order(self, coords):
        """Create and dispatch an order from ``[rx, ry, cx, cy]``.

        Returns a dict with keys: order, rider, new_rider (Rider or None),
        route (list of points), route_length, eta.
        """
        rx, ry, cx, cy = [int(v) for v in coords]
        order = Order((rx, ry), (cx, cy))
        self.orders.append(order)
        new_rider = None
        if not self.system.idle_riders():
            new_rider = self.system.recruit_rider()
        rider = find_best_rider_for_order(order)
        if rider is not None and new_rider is None and \
                rider in self.system.riders and len(self.system.riders) == 1 \
                and rider.log and len(rider.log) == 1 and not rider.orders \
                and rider.rider_id == globalvar.get_value("rider_id_counter") \
                and rider.distance_travelled == 0 and rider.completed_count == 0:
            pass
        result = {"order": order, "rider": rider, "new_rider": new_rider,
                  "route": [], "route_length": 0, "eta": None}
        if rider is None:
            self.pending.append(order)
            return result
        self.assign(order, rider)
        route, length = self.plan_route(rider, order)
        result["route"] = route
        result["route_length"] = length
        result["eta"] = -(-length // rider.speed) if rider.speed else None
        return result

    def plan_route(self, rider, order):
        """Plan the full route of ``rider`` for ``order``.

        Starts at the rider position (or the previous order's customer if
        the rider is busy).  Returns ``(points, length)`` where ``points``
        includes the starting point.
        """
        idx = rider.orders.index(order) if order in rider.orders else -1
        if idx > 0:
            start = tuple(rider.orders[idx - 1].cus_pos)
        else:
            start = (rider.x, rider.y)
        path = self.planner.plan_multi(start, [order.res_pos, order.cus_pos])
        length = self.planner.path_length(start, path)
        return [start] + path, length

    def process_pending(self):
        """Try to assign orders still waiting for a rider."""
        pending = self.pending
        if not pending:
            return
        for order in list(pending):
            if not self.system.idle_riders():
                self.system.recruit_rider()
            rider = find_best_rider_for_order(order)
            if rider is None:
                break
            self.assign(order, rider)
            pending.remove(order)

    def completed_orders(self):
        """All completed orders."""
        return [o for o in self.orders if o.status == "completed"]
