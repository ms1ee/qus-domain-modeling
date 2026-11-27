"""Order management: creation, assignment and nearest-rider selection."""

import logging
import math

from globalvar import get_value
from grid import validate_coordinate
from order_model import Order
from rider import IDLE

logger = logging.getLogger("dispatch.order")


def find_best_rider_for_order(order) -> "Rider":
    """Select the rider best suited to serve an order.

    Strategy: closest rider first by Euclidean distance from the rider to
    the restaurant. Idle riders are preferred. If no rider is idle, the
    rider with the fewest assigned orders (then closest) is chosen to
    balance load.

    Args:
        order: The Order to be assigned.

    Returns:
        The selected Rider, or None if no riders exist.
    """
    riders = get_value("riders", []) or []
    if not riders:
        return None

    rest_x, rest_y = order.res_pos

    def distance(rider):
        return math.sqrt((rider.x - rest_x) ** 2 + (rider.y - rest_y) ** 2)

    idle = [r for r in riders if r.state == IDLE and not r.orders]
    if idle:
        return min(idle, key=distance)
    return min(riders, key=lambda r: (len(r.orders), distance(r)))


class OrderManager:
    """Creates, assigns and tracks delivery orders."""

    def create_order(self, rest_x, rest_y, cus_x, cus_y) -> Order:
        """Validate raw coordinates and create a pending order.

        Args:
            rest_x: Restaurant x coordinate (0-800).
            rest_y: Restaurant y coordinate (0-800).
            cus_x: Customer x coordinate (0-800).
            cus_y: Customer y coordinate (0-800).

        Returns:
            The newly created Order, also registered as pending.

        Raises:
            ValueError: If any coordinate is invalid.
        """
        values = [validate_coordinate(v)
                  for v in (rest_x, rest_y, cus_x, cus_y)]
        order = Order((values[0], values[1]), (values[2], values[3]))
        get_value("orders").append(order)
        get_value("pending_orders").append(order)
        logger.info("Created order %s", order.id)
        return order

    def pending_orders(self) -> list:
        """Return the list of orders not yet assigned to a rider."""
        return list(get_value("pending_orders", []))

    def assign(self, order):
        """Assign an order to the best rider and queue it on that rider.

        Args:
            order: The Order to assign.

        Returns:
            The Rider that received the order, or None if no rider exists
            (the order then stays pending).
        """
        rider = find_best_rider_for_order(order)
        if rider is None:
            logger.warning("No rider available for order %s", order.id)
            return None
        order.assign_to(rider.rider_id)
        rider.orders.append(order)
        pending = get_value("pending_orders")
        if order in pending:
            pending.remove(order)
        return rider

    def assign_all_pending(self) -> list:
        """Try to assign every pending order; return the riders used."""
        used = []
        for order in self.pending_orders():
            rider = self.assign(order)
            if rider is not None:
                used.append(rider)
        return used

    def completed_orders(self) -> list:
        """Return all orders that have been delivered."""
        return [o for o in get_value("orders", []) if o.status == "completed"]
