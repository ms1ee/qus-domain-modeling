"""Order management: creation, rider assignment and lookup."""

import logging

import globalvar
from config import CONFIG
from order_model import Order

logger = logging.getLogger("dispatch")

# Score penalty per already-queued order, used for load balancing.
LOAD_PENALTY = 200


def find_best_rider_for_order(order):
    """Find the best rider for an order.

    Strategy: closest rider first (Manhattan distance from the rider to the
    restaurant). A load penalty per queued order makes busy riders less
    attractive, so work is spread across riders. Riders already holding
    ``max_orders_per_rider`` orders are skipped.

    Args:
        order: The Order to assign.

    Returns:
        The selected Rider, or None if no rider can accept the order.
    """
    riders = globalvar.get_value("riders") or []
    rest_x, rest_y = order.restaurant_center
    max_orders = int(CONFIG["max_orders_per_rider"])
    best = None
    best_score = None
    for rider in riders:
        if len(rider.orders) >= max_orders:
            continue
        distance = abs(rider.x - rest_x) + abs(rider.y - rest_y)
        score = distance + LOAD_PENALTY * len(rider.orders)
        if best is None or (score, rider.rider_id) < (best_score, best.rider_id):
            best = rider
            best_score = score
    return best


class OrderManager:
    """Creates, assigns and tracks orders for the dispatch system.

    Attributes:
        system: The SystemManager that owns funds and riders.
    """

    def __init__(self, system):
        """Create an order manager bound to a system.

        Args:
            system: SystemManager instance.
        """
        self.system = system

    @property
    def orders(self):
        """Return the list of all orders."""
        return globalvar.get_value("orders")

    def create_order(self, restaurant_pos, customer_pos):
        """Create an order, register it and collect the order fee.

        Args:
            restaurant_pos: (x, y) restaurant position.
            customer_pos: (x, y) customer position.

        Returns:
            The new Order.
        """
        order = Order(restaurant_pos, customer_pos)
        self.orders.append(order)
        self.system.add_funds(CONFIG["order_fee"])
        logger.info("Order %s created", order.id)
        return order

    def assign(self, order):
        """Assign an order to the best available rider.

        Args:
            order: Order to assign.

        Returns:
            The rider that accepted the order, or None if none is available.
        """
        rider = find_best_rider_for_order(order)
        if rider is None:
            order.status = "unassigned"
            logger.warning("No rider available for order %s", order.id)
            return None
        order.assign_to(rider.rider_id)
        rider.orders.append(order)
        logger.info("Order %s assigned to rider %s", order.id, rider.rider_id)
        return rider

    def dispatch_pending(self):
        """Retry assignment for orders that could not be assigned earlier."""
        for order in self.orders:
            if order.status == "unassigned":
                self.assign(order)

    def get_order(self, order_id):
        """Return the order with ``order_id`` or None."""
        for order in self.orders:
            if order.id == order_id:
                return order
        return None

    def active_orders(self):
        """Return orders that are not yet completed."""
        return [order for order in self.orders if order.status != "completed"]

    def completed_orders(self):
        """Return completed orders."""
        return [order for order in self.orders if order.status == "completed"]
