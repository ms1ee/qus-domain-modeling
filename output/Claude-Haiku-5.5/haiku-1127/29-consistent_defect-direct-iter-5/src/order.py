"""Order creation, rider assignment and order bookkeeping."""

import logging

from globalvar import get_value, set_value
from order_model import ORDER_PENDING, Order
from path_planner import PathPlanner

logger = logging.getLogger(__name__)

COORD_MIN = 0
COORD_MAX = 1000
COORD_LABELS = ("restaurant_x", "restaurant_y", "customer_x", "customer_y")


def _riders():
    """Return the global rider list, creating it if missing."""
    riders = get_value("riders")
    if riders is None:
        riders = []
        set_value("riders", riders)
    return riders


def _orders():
    """Return the global order history list, creating it if missing."""
    orders = get_value("orders")
    if orders is None:
        orders = []
        set_value("orders", orders)
    return orders


def validate_order_coordinates(values):
    """Validate the four order coordinates.

    Args:
        values: Sequence ``[restaurant_x, restaurant_y, customer_x, customer_y]``.

    Returns:
        A list of four validated integers.

    Raises:
        ValueError: If the count is wrong, a value is not an integer, or a
            value lies outside 0-1000.
    """
    values = list(values)
    if len(values) != 4:
        raise ValueError(f"Expected 4 coordinates, got {len(values)}.")
    result = []
    for label, value in zip(COORD_LABELS, values):
        if isinstance(value, bool) or not isinstance(value, int):
            raise ValueError(f"{label} must be an integer.")
        if not COORD_MIN <= value <= COORD_MAX:
            raise ValueError(
                f"{label} must be between {COORD_MIN} and {COORD_MAX}, got {value}."
            )
        result.append(value)
    return result


def find_best_rider_for_order(order):
    """Select the best rider for an order using a distance-first strategy.

    The rider closest to the restaurant (Euclidean distance
    ``sqrt((rider_x - restaurant_x)^2 + (rider_y - restaurant_y)^2)``) is
    chosen. Ties are broken by the rider's current number of active orders,
    then by rider ID.

    Args:
        order: The ``Order`` to assign.

    Returns:
        The selected ``Rider``, or None if no riders exist.
    """
    riders = _riders()
    if not riders:
        return None
    best = None
    best_key = None
    for rider in riders:
        distance = PathPlanner.euclidean(rider.position(), order.res_pos)
        key = (distance, len(rider.active_orders()), rider.rider_id)
        if best_key is None or key < best_key:
            best = rider
            best_key = key
    logger.debug("Order %d -> rider %s (distance %.1f)",
                 order.id, best.rider_id, best_key[0])
    return best


class OrderManager:
    """Creates, assigns and queries orders."""

    def create_order(self, restaurant, customer, tick=0):
        """Validate coordinates and create a pending order.

        Args:
            restaurant: ``(x, y)`` restaurant coordinates, range 0-1000.
            customer: ``(x, y)`` customer coordinates, range 0-1000.
            tick: Current simulation tick.

        Returns:
            The newly created ``Order`` (also stored in the order history).

        Raises:
            ValueError: If any coordinate is invalid.
        """
        res = validate_order_coordinates(list(restaurant) + list(customer))
        order = Order((res[0], res[1]), (res[2], res[3]), created_tick=tick)
        _orders().append(order)
        logger.info("Order %d created", order.id)
        return order

    def assign(self, order, rider, tick=0):
        """Assign a pending order to a rider.

        Args:
            order: A pending ``Order``.
            rider: The ``Rider`` receiving the order.
            tick: Current simulation tick.

        Raises:
            ValueError: If the order is not pending.
        """
        if order.status != ORDER_PENDING:
            raise ValueError(f"Order {order.id} is not pending.")
        order.assign_to(rider.rider_id, tick)
        rider.orders.append(order)

    def pending_orders(self):
        """Return all orders still waiting for a rider, oldest first."""
        return [o for o in _orders() if o.status == ORDER_PENDING]

    def all_orders(self):
        """Return a copy of the full order history."""
        return list(_orders())

    def completed_orders(self):
        """Return all completed orders."""
        return [o for o in _orders() if o.status == "completed"]
