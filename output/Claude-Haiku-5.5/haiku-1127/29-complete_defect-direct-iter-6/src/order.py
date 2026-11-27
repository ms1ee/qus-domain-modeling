"""Order creation, assignment and the closest-rider selection strategy."""

import logging

import globalvar
from order_model import Order

logger = logging.getLogger("dispatch.order")

QUEUE_PENALTY = 150


def find_best_rider_for_order(order):
    """Select the rider that should receive ``order``.

    Strategy: closest rider first. Each rider's score is the Manhattan
    distance from its position to the restaurant plus a penalty per queued
    order, which balances load between riders. Ties are broken by lower ID.

    Args:
        order: The Order to be assigned.

    Returns:
        The selected Rider, or None when no riders exist.
    """
    riders = globalvar.get_value("riders", [])
    best = None
    best_score = None
    for rider in riders:
        distance = abs(rider.x - order.res_center[0]) + abs(rider.y - order.res_center[1])
        score = distance + QUEUE_PENALTY * len(rider.orders)
        if best is None or (score, rider.rider_id) < (best_score, best.rider_id):
            best = rider
            best_score = score
    return best


class OrderManager:
    """Creates orders, assigns them to riders and tracks pending orders."""

    def create_order(self, res_pos, cus_pos):
        """Create an order from raw coordinates and register it globally.

        Args:
            res_pos: ``[x, y]`` restaurant coordinate.
            cus_pos: ``[x, y]`` customer coordinate.

        Returns:
            The new Order.

        Raises:
            ValueError: If coordinates are invalid.
        """
        order = Order(res_pos, cus_pos)
        globalvar.get_value("orders").append(order)
        logger.info("order %s created", order.id)
        return order

    def assign_order(self, order):
        """Assign an order to the best rider, or queue it as pending.

        Args:
            order: An order in the "created" status.

        Returns:
            The Rider receiving the order, or None if the order is pending.
        """
        rider = find_best_rider_for_order(order)
        if rider is None:
            pending = globalvar.get_value("pending_orders")
            if order not in pending:
                pending.append(order)
            logger.warning("no rider available for order %s; queued", order.id)
            return None
        order.assign_to(rider.rider_id)
        logger.info("order %s assigned to rider %s", order.id, rider.rider_id)
        return rider

    def assign_pending(self):
        """Assign queued orders to riders as they become available.

        Returns:
            List of orders assigned during this call.
        """
        pending = globalvar.get_value("pending_orders")
        assigned = []
        for order in list(pending):
            rider = find_best_rider_for_order(order)
            if rider is None:
                break
            order.assign_to(rider.rider_id)
            pending.remove(order)
            assigned.append(order)
        return assigned

    def all_orders(self):
        """Return every order created in this session."""
        return list(globalvar.get_value("orders", []))
