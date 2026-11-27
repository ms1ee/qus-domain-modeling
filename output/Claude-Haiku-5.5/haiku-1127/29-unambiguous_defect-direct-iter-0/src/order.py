"""Order management: creation, rider assignment and order history."""

import logging

from globalvar import get_value, set_value
from order_model import Order
from path_planner import PathPlanner

logger = logging.getLogger(__name__)

ASSIGN_LOAD_PENALTY = 150


def rider_score(rider, order):
    """Compute the assignment cost of giving ``order`` to ``rider``.

    The score is distance-first: the rider's street distance to the
    restaurant, plus a load penalty per order already assigned to the rider
    (which balances work across riders).

    Args:
        rider: Candidate Rider.
        order: Order to be assigned.

    Returns:
        Integer cost; lower is better.
    """
    distance = PathPlanner.manhattan(rider.position, order.res_pos)
    return distance + ASSIGN_LOAD_PENALTY * len(rider.orders)


def find_best_rider_for_order(order):
    """Select the most suitable rider for an order.

    Args:
        order: The Order needing a rider.

    Returns:
        The Rider with the lowest assignment score (ties broken by ID),
        or None if no riders exist.
    """
    riders = get_value("riders") or []
    if not riders:
        return None
    return min(riders, key=lambda r: (rider_score(r, order), r.rider_id))


class OrderManager:
    """Coordinates order creation, assignment and history bookkeeping."""

    @staticmethod
    def _history():
        """Return the order history list, creating it if necessary."""
        history = get_value("order_history")
        if history is None:
            history = []
            set_value("order_history", history)
        return history

    def create_order(self, res_pos, cus_pos):
        """Create an order from raw coordinates and register its locations.

        Args:
            res_pos: Raw restaurant coordinates ``(x, y)``.
            cus_pos: Raw customer coordinates ``(x, y)``.

        Returns:
            The newly created Order.

        Raises:
            ValueError: If any coordinate is invalid.
        """
        order = Order(res_pos, cus_pos)
        self._history().append(order)
        restaurants = get_value("restaurants")
        customers = get_value("customers")
        if restaurants is not None:
            restaurants.add(order.res_pos)
        if customers is not None:
            customers.add(order.cus_pos)
        logger.info("Created order %d: %s -> %s", order.id, order.res_pos, order.cus_pos)
        return order

    def assign_order(self, order, rider=None):
        """Assign an order to the best rider (or a given rider).

        Args:
            order: Order to assign.
            rider: Optional explicit rider; if None the best rider is chosen.

        Returns:
            The rider the order was assigned to, or None if no rider exists.
        """
        if rider is None:
            rider = find_best_rider_for_order(order)
        if rider is None:
            order.status = "unassigned"
            logger.warning("No rider available for order %d", order.id)
            return None
        rider.orders.append(order)
        order.assign_to(rider.rider_id)
        logger.info("Assigned order %d to rider %d", order.id, rider.rider_id)
        return rider

    def history(self):
        """Return every order created in this session.

        Returns:
            List of Order objects in creation order.
        """
        return list(self._history())
