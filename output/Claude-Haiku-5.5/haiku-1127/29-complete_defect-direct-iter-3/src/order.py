"""Order management: rider assignment and the order registry."""

import logging

import globalvar
from order_model import Order
from path_planner import manhattan
from rider import Rider

logger = logging.getLogger(__name__)

# Distance-equivalent penalty per already-queued order, to balance load.
LOAD_PENALTY = 150


def find_best_rider_for_order(order):
    """Choose the best rider for ``order`` using distance-first assignment.

    The cost of a rider is its Manhattan distance to the restaurant plus a
    load penalty for each order it already carries. The lowest cost wins, with
    the lower rider ID breaking ties.

    Args:
        order: Order whose restaurant position is the pickup point.

    Returns:
        The selected Rider, or None if no riders exist.
    """
    riders = globalvar.get_value("riders") or []
    best = None
    best_cost = None
    for rider in riders:
        distance = manhattan(rider.position, order.res_pos)
        cost = distance + LOAD_PENALTY * len(rider.orders)
        if (best is None or cost < best_cost
                or (cost == best_cost and rider.rider_id < best.rider_id)):
            best = rider
            best_cost = cost
    return best


class OrderManager:
    """Creates, assigns and queries orders for the simulation."""

    def create_order(self, res_pos, cus_pos):
        """Create an order and register it in the global order list.

        Args:
            res_pos: ``[x, y]`` restaurant position (0-800).
            cus_pos: ``[x, y]`` customer position (0-800).

        Returns:
            The newly created Order.
        """
        order = Order(res_pos, cus_pos)
        orders = globalvar.get_value("orders")
        if orders is None:
            orders = []
            globalvar.set_value("orders", orders)
        orders.append(order)
        logger.info("Created order #%s", order.id)
        return order

    def assign_order(self, order):
        """Assign ``order`` to the best rider by appending it to rider.orders.

        Args:
            order: Order to assign.

        Returns:
            The rider that received the order, or None if no rider exists.
        """
        rider = find_best_rider_for_order(order)
        if rider is None:
            logger.warning("No rider available for order #%s", order.id)
            return None
        order.assign_to(rider.rider_id)
        rider.orders.append(order)
        logger.info("Order #%s assigned to rider #%s", order.id, rider.rider_id)
        return rider

    def all_orders(self):
        """Return a copy of every order created in this session."""
        return list(globalvar.get_value("orders") or [])

    def active_orders(self):
        """Return orders that are not yet completed."""
        return [o for o in self.all_orders() if o.status != "completed"]

    def find_order(self, order_id):
        """Return the order with ``order_id``, or None."""
        for order in self.all_orders():
            if order.id == order_id:
                return order
        return None
