"""Order management: rider selection, assignment and order bookkeeping."""

import logging
import math

import globalvar
from order_model import Order, validate_order_coordinates
from path_planner import PathPlanner

logger = logging.getLogger(__name__)


def find_best_rider_for_order(order):
    """Select the rider closest to the order's restaurant.

    Distance is Euclidean: ``sqrt((rider_x - restaurant_x)^2 +
    (rider_y - restaurant_y)^2)``. Ties are broken by the smaller number of
    current orders (load balancing) and then by rider id.

    Args:
        order: Order whose ``res_pos`` is the pickup location.

    Returns:
        The best Rider, or None when no riders exist.
    """
    riders = globalvar.get_value("riders") or []
    best = None
    best_key = None
    for rider in riders:
        distance = math.hypot(rider.x - order.res_pos[0], rider.y - order.res_pos[1])
        key = (distance, len(rider.orders), rider.rider_id)
        if best_key is None or key < best_key:
            best = rider
            best_key = key
    return best


class OrderManager:
    """Creates orders, assigns them to riders and tracks their history."""

    def __init__(self):
        """Create an order manager with its own path planner."""
        self._planner = PathPlanner()

    def create_order(self, coords):
        """Validate coordinates, create an order and queue it as pending.

        Args:
            coords: Sequence ``[restaurant_x, restaurant_y, customer_x, customer_y]``.

        Returns:
            The created Order.

        Raises:
            ValueError: If the input has the wrong length or is out of range.
            TypeError: If an input value is not an integer.
        """
        res_x, res_y, cus_x, cus_y = validate_order_coordinates(coords)
        order = Order((res_x, res_y), (cus_x, cus_y))
        globalvar.get_value("orders").append(order)
        globalvar.get_value("pending_orders").append(order)
        logger.info("Created order %s", order.id)
        return order

    def pending_orders(self):
        """Return a copy of the list of orders waiting for a rider."""
        return list(globalvar.get_value("pending_orders") or [])

    def completed_orders(self):
        """Return all orders that have been delivered."""
        return [o for o in (globalvar.get_value("orders") or [])
                if o.status == "completed"]

    def assign_order(self, order, rider):
        """Assign an order to a rider by appending it to the rider's orders.

        Args:
            order: Order to assign.
            rider: Rider receiving the order.
        """
        order.assign_to(rider.rider_id)
        order.distance = PathPlanner.route_length(
            order.res_pos, self._planner.plan(order.res_pos, order.cus_pos))
        rider.orders.append(order)
        pending = globalvar.get_value("pending_orders")
        if order in pending:
            pending.remove(order)
        logger.info("Assigned order %s to rider %s", order.id, rider.rider_id)

    def assign_pending(self):
        """Assign every pending order to its nearest rider.

        Returns:
            List of ``(order, rider)`` tuples for orders assigned in this call.
        """
        assigned = []
        for order in self.pending_orders():
            rider = find_best_rider_for_order(order)
            if rider is None:
                break
            self.assign_order(order, rider)
            assigned.append((order, rider))
        return assigned

    def estimate_route(self, rider, order):
        """Plan the rider's route: current position -> restaurant -> customer.

        Args:
            rider: Rider whose current position is the start.
            order: Order whose legs are planned.

        Returns:
            Tuple ``(points, total_length)`` where points are the waypoints
            (excluding the rider position) and total_length is in units.
        """
        first_leg = self._planner.plan(rider.position, order.res_pos)
        second_leg = self._planner.plan(order.res_pos, order.cus_pos)
        points = first_leg + second_leg
        total = PathPlanner.route_length(rider.position, points)
        return points, total
