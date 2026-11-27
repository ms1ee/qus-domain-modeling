"""Order creation, assignment and bookkeeping."""

import logging

import globalvar
from order_model import Order
from path_planner import PathPlanner
from input_manager import InputManager

logger = logging.getLogger(__name__)


def find_best_rider_for_order(order, riders=None):
    """Select the most suitable rider for ``order``.

    Strategy: riders with fewer assigned orders win (load balancing);
    among equally loaded riders the one with the smallest Manhattan
    distance to the restaurant wins; ties broken by rider id.
    Returns None if there are no riders.
    """
    if riders is None:
        riders = globalvar.get_value("riders") or []
    if not riders:
        return None

    def key(rider):
        load = len([o for o in rider.orders if getattr(o, "status", None) != "completed"])
        busy = 0 if rider.state == 0 else 1
        dist = PathPlanner.manhattan((rider.x, rider.y), order.res_pos)
        return (load, busy, dist, rider.rider_id)

    return min(riders, key=key)


class OrderManager:
    """Handles order creation, assignment and completion queries."""

    def __init__(self, system_manager):
        self.system = system_manager

    @staticmethod
    def all_orders():
        """All orders known to the system."""
        return globalvar.get_value("orders") or []

    def active_orders(self):
        """Orders not yet completed."""
        return [o for o in self.all_orders() if o.status != "completed"]

    def completed_orders(self):
        """Completed orders."""
        return [o for o in self.all_orders() if o.status == "completed"]

    def create_order(self, coords):
        """Validate coordinates and create an Order."""
        values = InputManager.parse_coordinates(coords)
        return Order((values[0], values[1]), (values[2], values[3]))

    def place_order(self, coords):
        """Create and assign an order.

        Returns a dict with keys: order, rider, recruited (Rider or None),
        route_start, route, route_length, est_ticks.
        """
        values = InputManager.parse_coordinates(coords)
        recruited = self.system.auto_recruit()
        if not self.system.riders:
            raise RuntimeError("No rider available and insufficient funds to recruit one.")
        order = Order((values[0], values[1]), (values[2], values[3]))
        rider = find_best_rider_for_order(order, self.system.riders)
        if rider is None:
            raise RuntimeError("No rider available.")
        # Determine where the rider will start this order from.
        pending = [o for o in rider.orders if o.status != "completed"]
        if pending:
            route_start = pending[-1].cus_pos
        else:
            route_start = (rider.x, rider.y)
        rider.orders.append(order)
        order.assign_to(rider.rider_id)
        route = PathPlanner.plan_multi(route_start, [order.res_pos, order.cus_pos])
        length = PathPlanner.path_length(route_start, route)
        est = -(-length // rider.speed) + 1
        logger.info("Order %d assigned to rider %d", order.id, rider.rider_id)
        return {
            "order": order,
            "rider": rider,
            "recruited": recruited,
            "route_start": route_start,
            "route": route,
            "route_length": length,
            "est_ticks": est,
        }
