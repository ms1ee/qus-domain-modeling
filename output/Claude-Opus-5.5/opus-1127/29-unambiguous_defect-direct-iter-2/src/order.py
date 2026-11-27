"""Order management: creation, assignment and completion tracking."""

import logging
import math

import globalvar
import system
from order_model import Order
from path_planner import PathPlanner, manhattan

logger = logging.getLogger(__name__)


def find_best_rider_for_order(order):
    """Select the most suitable rider for ``order``.

    Strategy:
      1. The idle rider closest (Manhattan distance) to the restaurant.
      2. Otherwise recruit a new rider if funds/limits allow (or if no
         rider exists at all).
      3. Otherwise the busy rider with the smallest estimated finishing
         distance (current workload + distance to the restaurant), which
         balances load between riders.

    Sets the global flag ``last_rider_added``. Does not append the order.
    """
    riders = globalvar.get_value("riders")
    if riders is None:
        riders = []
        globalvar.set_value("riders", riders)
    globalvar.set_value("last_rider_added", False)
    target = order.res_pos

    idle = [r for r in riders if r.state == 0 and not r.orders]
    if idle:
        return min(idle, key=lambda r: (manhattan((r.x, r.y), target),
                                        r.rider_id))

    if not riders or system.can_recruit():
        rider = system.recruit_rider()
        globalvar.set_value("last_rider_added", True)
        return rider

    def score(r):
        pos, dist = r.workload()
        return (dist + manhattan(pos, target), len(r.orders), r.rider_id)

    return min(riders, key=score)


class OrderManager:
    """Creates orders, assigns them and reports results."""

    def __init__(self):
        self.planner = PathPlanner()

    @property
    def orders(self):
        orders = globalvar.get_value("orders")
        if orders is None:
            orders = []
            globalvar.set_value("orders", orders)
        return orders

    def create_order(self, coords):
        """Create and register an order from ``[rx, ry, cx, cy]``."""
        if len(coords) != 4:
            raise ValueError("an order needs exactly 4 coordinates")
        order = Order((coords[0], coords[1]), (coords[2], coords[3]))
        self.orders.append(order)
        return order

    def assign(self, order):
        """Assign ``order`` to the best rider.

        Returns a dict with keys: rider, added, route, distance, eta.
        """
        rider = find_best_rider_for_order(order)
        added = bool(globalvar.get_value("last_rider_added", False))
        start_pos, pre_dist = rider.workload()
        route = self.planner.plan_route(start_pos,
                                        [order.res_pos, order.cus_pos])
        route_len = self.planner.route_length(route)
        total = pre_dist + route_len
        eta = math.ceil(total / rider.speed) if rider.speed else None
        rider.orders.append(order)
        order.assign_to(rider.rider_id)
        logger.info("Order %s assigned to rider %s", order.id,
                    rider.rider_id)
        return {"rider": rider, "added": added, "route": route,
                "distance": route_len, "total_distance": total,
                "eta": eta}

    def place_order(self, coords):
        """Create and assign an order in one step."""
        order = self.create_order(coords)
        result = self.assign(order)
        result["order"] = order
        return result

    def completed_orders(self):
        """Return all completed orders."""
        return [o for o in self.orders if o.status == "completed"]

    def statistics(self):
        """Simple efficiency statistics for completed orders."""
        done = self.completed_orders()
        if not done:
            return {"completed": 0, "avg_time": None, "avg_efficiency": None}
        times = [o.time_taken for o in done]
        effs = [o.efficiency for o in done if o.efficiency]
        return {
            "completed": len(done),
            "avg_time": round(sum(times) / len(times), 2),
            "avg_efficiency": round(sum(effs) / len(effs), 3) if effs
            else None,
        }
