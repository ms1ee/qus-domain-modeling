"""Order management: rider matching, assignment, pending queue and history."""

import logging

import globalvar
from order_model import STATUS_COMPLETED, Order
from path_planner import manhattan

logger = logging.getLogger(__name__)

DEFAULT_LOAD_PENALTY = 200


def find_best_rider_for_order(order):
    """Choose the best rider for an order.

    The primary criterion is distance: the rider closest to the restaurant
    is preferred. Each order already held by a rider adds a load penalty,
    which balances the workload among competing riders. Ties are resolved
    in favour of the lower rider ID.

    Args:
        order: The Order that needs a rider.

    Returns:
        The selected Rider, or None if no riders exist.
    """
    riders = globalvar.get_value("riders") or []
    config = globalvar.get_value("config") or {}
    penalty = int(config.get("load_penalty", DEFAULT_LOAD_PENALTY))

    best = None
    best_score = None
    for rider in riders:
        distance = manhattan(rider.position, order.restaurant_pos)
        score = distance + penalty * len(rider.orders)
        if (
            best is None
            or score < best_score
            or (score == best_score and rider.rider_id < best.rider_id)
        ):
            best = rider
            best_score = score
    return best


class OrderManager:
    """Creates, assigns and tracks orders.

    Attributes:
        orders: Full order history (active and completed).
        pending: Orders waiting for a rider to become available.
    """

    def __init__(self):
        """Create an empty order manager."""
        self.orders = []
        self.pending = []

    def create_order(self, restaurant_pos, customer_pos):
        """Create and register a new order.

        Args:
            restaurant_pos: Raw restaurant position ``(x, y)``.
            customer_pos: Raw customer position ``(x, y)``.

        Returns:
            The created Order.
        """
        order = Order(restaurant_pos, customer_pos)
        self.orders.append(order)
        logger.info("Created order %s", order.id)
        return order

    def assign_order(self, order):
        """Assign an order to the best rider, or queue it as pending.

        Args:
            order: The Order to assign.

        Returns:
            The Rider receiving the order, or None if the order was queued.
        """
        rider = find_best_rider_for_order(order)
        if rider is None:
            if order not in self.pending:
                self.pending.append(order)
            logger.info("Order %s queued: no rider available", order.id)
            return None
        self._bind(order, rider)
        return rider

    def assign_pending(self):
        """Try to assign all pending orders in FIFO order.

        Returns:
            Number of orders assigned during this call.
        """
        assigned = 0
        for order in list(self.pending):
            rider = find_best_rider_for_order(order)
            if rider is None:
                break
            self._bind(order, rider)
            assigned += 1
        return assigned

    def active_orders(self):
        """Return orders that are not yet completed."""
        return [o for o in self.orders if o.status != STATUS_COMPLETED]

    def completed_orders(self):
        """Return completed orders."""
        return [o for o in self.orders if o.status == STATUS_COMPLETED]

    def _bind(self, order, rider):
        """Attach an order to a rider and update bookkeeping."""
        rider.orders.append(order)
        order.assign_to(rider.rider_id)
        if order in self.pending:
            self.pending.remove(order)
        logger.info("Order %s assigned to rider %s", order.id, rider.rider_id)
