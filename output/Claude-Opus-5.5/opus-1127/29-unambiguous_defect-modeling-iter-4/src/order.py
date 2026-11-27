"""Order management: creation, assignment and statistics."""

import logging

import globalvar
from order_model import Order
from path_planner import PathPlanner
from system import SystemManager

logger = logging.getLogger(__name__)


def find_best_rider_for_order(order):
    """Select the best rider for ``order``.

    Strategy:
      1. The nearest idle rider (street distance to the restaurant); ties are
         broken by fewer completed orders (load balancing) then rider id.
      2. If no rider is idle and funds allow, recruit a new rider.
         If there are no riders at all, a rider is always recruited.
      3. Otherwise the busy rider with the least estimated workload.

    The order is NOT appended to the rider's order list.
    """
    riders = globalvar.get_value("riders")
    if not isinstance(riders, list):
        riders = []
        globalvar.set_value("riders", riders)
    res = order.res_pos

    idle = [r for r in riders if r.is_idle()]
    if idle:
        return min(idle, key=lambda r: (PathPlanner.distance(r.position, res),
                                        r.completed_orders, r.rider_id))

    manager = SystemManager()
    if not riders or manager.can_recruit():
        rider = manager.recruit_rider(force=not riders)
        if rider is not None:
            return rider

    return min(riders, key=lambda r: (
        r.estimate_workload() + PathPlanner.distance(r.last_position(), res),
        len(r.active_orders()), r.rider_id))


class OrderManager:
    """Handles order creation, assignment and reporting."""

    def __init__(self, system=None):
        self.system = system or SystemManager()

    def create_order(self, coords):
        """Create an order from ``[restaurant_x, restaurant_y, customer_x, customer_y]``."""
        if len(coords) != 4:
            raise ValueError("an order needs exactly 4 coordinates")
        return Order((coords[0], coords[1]), (coords[2], coords[3]))

    def assign_order(self, order):
        """Assign ``order`` to the best rider.

        Returns:
            Tuple ``(rider, new_rider_added, route)`` where route is the
            planned :class:`Route` from the rider's start to the customer.
        """
        count_before = len(self.system.riders)
        rider = find_best_rider_for_order(order)
        new_rider = len(self.system.riders) > count_before
        start = rider.last_position()
        rider.orders.append(order)
        order.assign_to(rider.rider_id)
        route = PathPlanner.build_route(start, [order.res_pos, order.cus_pos], rider.speed)
        logger.info("Order %s assigned to rider %s", order.id, rider.rider_id)
        return rider, new_rider, route

    def place_order(self, coords):
        """Create and assign an order. Returns a result dict."""
        order = self.create_order(coords)
        rider, new_rider, route = self.assign_order(order)
        return {
            "order": order,
            "rider": rider,
            "new_rider": new_rider,
            "route": route,
        }

    def all_orders(self):
        """Return all orders."""
        return list(self.system.orders)

    def active_orders(self):
        """Return orders not yet completed."""
        return [o for o in self.system.orders if not o.is_completed()]

    def statistics(self):
        """Return delivery statistics."""
        done = [o for o in self.system.orders if o.is_completed()]
        avg_time = (sum(o.time_taken for o in done) / len(done)) if done else 0
        effs = [o.efficiency for o in done if o.efficiency]
        return {
            "total": len(self.system.orders),
            "completed": len(done),
            "active": len(self.system.orders) - len(done),
            "average_time": round(avg_time, 2),
            "average_efficiency": round(sum(effs) / len(effs), 2) if effs else 0,
        }
