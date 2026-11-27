"""Order management: creation, assignment and completion helpers."""

import logging
import math

import globalvar
from order_model import Order
from path_planner import PathPlanner

logger = logging.getLogger("dispatch.order")


def _manhattan(a, b):
    return abs(a[0] - b[0]) + abs(a[1] - b[1])


def projected_state(rider, exclude=None):
    """Return (cost, position) after the rider finishes its backlog.

    ``exclude`` is an order that should not be counted (e.g. the order
    currently being evaluated).
    """
    pos = (rider.x, rider.y)
    cost = 0
    for i, o in enumerate(rider.orders):
        if o is exclude or getattr(o, "status", None) == "completed":
            continue
        if o is rider.current_order and rider.state != 0:
            if rider.state == 1:
                cost += rider.remaining_distance() + o.distance
            else:
                cost += rider.remaining_distance()
        else:
            cost += PathPlanner.distance(pos, o.res_pos) + o.distance
        pos = o.cus_pos
    return cost, pos


def estimate_cost(rider, order):
    """Estimated distance before ``rider`` could reach the restaurant."""
    cost, pos = projected_state(rider, exclude=order)
    return cost + PathPlanner.distance(pos, order.res_pos)


def find_best_rider_for_order(order, riders=None):
    """Return the best rider for ``order`` (closest first, load balanced).

    Idle riders are ranked by their distance to the restaurant; busy riders
    include their remaining backlog distance, so work spreads across riders.
    Returns None if there are no riders.
    """
    if riders is None:
        riders = globalvar.get_value("riders") or []
    if not riders:
        return None
    return min(riders, key=lambda r: (estimate_cost(r, order),
                                      len(r.orders), r.rider_id))


class OrderManager:
    """Handles order creation, assignment and querying."""

    def __init__(self, system_manager=None):
        self.system_manager = system_manager

    @staticmethod
    def all_orders():
        """Return list of all orders."""
        orders = globalvar.get_value("orders")
        if orders is None:
            orders = []
            globalvar.set_value("orders", orders)
        return orders

    @staticmethod
    def validate_coordinates(coords):
        """Validate four coordinates; raise ValueError on error."""
        if len(coords) != 4:
            raise ValueError("Exactly four coordinates are required.")
        out = []
        for c in coords:
            if isinstance(c, bool) or not isinstance(c, int):
                raise ValueError("Coordinates must be integers.")
            if c < 0 or c > 800:
                raise ValueError("Coordinate %d out of range (0-800)." % c)
            out.append(c)
        return out

    def assign(self, order, rider):
        """Assign ``order`` to ``rider``."""
        order.assign_to(rider.rider_id)
        rider.orders.append(order)
        logger.info("Order %s assigned to rider %s", order.id, rider.rider_id)

    def create_order(self, rx, ry, cx, cy):
        """Create, store and assign an order.

        Returns a dict with keys: order, rider, new_rider, route, eta, cost.
        """
        self.validate_coordinates([rx, ry, cx, cy])
        order = Order((rx, ry), (cx, cy))
        self.all_orders().append(order)
        new_rider = None
        if self.system_manager is not None:
            new_rider = self.system_manager.auto_recruit()
        rider = find_best_rider_for_order(order)
        result = {"order": order, "rider": rider, "new_rider": new_rider,
                  "route": [], "eta": None, "cost": None}
        if rider is None:
            logger.warning("No rider available for order %s", order.id)
            return result
        backlog, start = projected_state(rider, exclude=order)
        route = PathPlanner.plan_multi(start, [order.res_pos, order.cus_pos])
        total = backlog + PathPlanner.path_length(route)
        self.assign(order, rider)
        result["route"] = route
        result["cost"] = total
        result["eta"] = int(math.ceil(total / float(max(rider.speed, 1))))
        return result
