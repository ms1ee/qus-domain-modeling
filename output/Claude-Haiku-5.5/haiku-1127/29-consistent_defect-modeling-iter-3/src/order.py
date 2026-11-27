"""Order management: validation, creation, assignment and rider selection."""

import logging
import math

import globalvar
from order_model import Order

COORD_MIN = 0
COORD_MAX = 1000

logger = logging.getLogger(__name__)


def validate_coordinates(values):
    """Validate four integer coordinates in the range 0-1000.

    Args:
        values: Sequence of four values
            ``[restaurant_x, restaurant_y, customer_x, customer_y]``.

    Returns:
        A list of the four validated integers.

    Raises:
        ValueError: If the count is wrong, a value is not an integer, or a
            value is out of range.
    """
    values = list(values)
    if len(values) != 4:
        raise ValueError(
            "Expected 4 coordinates: restaurant_x restaurant_y customer_x customer_y"
        )
    result = []
    for value in values:
        if isinstance(value, bool) or not isinstance(value, int):
            raise ValueError(f"Coordinate {value!r} is not an integer")
        if not COORD_MIN <= value <= COORD_MAX:
            raise ValueError(
                f"Coordinate {value} is out of range {COORD_MIN}-{COORD_MAX}"
            )
        result.append(value)
    return result


def _euclidean(x1, y1, x2, y2):
    """Return the Euclidean distance between two points."""
    return math.sqrt((x1 - x2) ** 2 + (y1 - y2) ** 2)


def find_best_rider_for_order(order):
    """Select the rider that should receive ``order``.

    The rider with the fewest active orders is preferred. Ties are broken by
    the distance from the rider to the restaurant.

    Args:
        order: The ``Order`` to be assigned.

    Returns:
        The selected ``Rider``, or None when no rider exists.
    """
    riders = globalvar.get_value("riders") or []
    if not riders:
        logger.warning("No riders available for order %s", order.id)
        return None
    rest_x, rest_y = order.res_pos

    def sort_key(rider):
        return (
            len(rider.active_orders()),
            _euclidean(rider.x, rider.y, rest_x, rest_y),
        )

    return min(riders, key=sort_key)


class OrderManager:
    """Keeps the order registry and performs order assignment.

    Attributes:
        orders (list[Order]): All orders created during this session.
    """

    def __init__(self):
        """Create an empty order registry."""
        self.orders = []

    def create_order(self, restaurant_xy, customer_xy):
        """Validate coordinates and create a new pending order.

        Args:
            restaurant_xy: ``(x, y)`` restaurant coordinates.
            customer_xy: ``(x, y)`` customer coordinates.

        Returns:
            The newly created ``Order``.

        Raises:
            ValueError: If coordinates are invalid.
        """
        values = validate_coordinates([*restaurant_xy, *customer_xy])
        order = Order((values[0], values[1]), (values[2], values[3]))
        self.orders.append(order)
        logger.info("Created order %s", order.id)
        return order

    def assign_order(self, order, rider):
        """Assign ``order`` to ``rider`` by appending it to the rider's orders.

        Args:
            order: The ``Order`` to assign.
            rider: The ``Rider`` receiving the order.
        """
        rider.orders.append(order)
        order.assign_to(rider.rider_id)
        rider.accept_pending_orders()
        logger.info("Order %s assigned to rider %s", order.id, rider.rider_id)

    def pending_orders(self):
        """Return orders that have not been assigned to any rider yet."""
        return [order for order in self.orders if order.status == "pending"]

    def completed_orders(self):
        """Return orders that have been delivered."""
        return [order for order in self.orders if order.status == "completed"]
