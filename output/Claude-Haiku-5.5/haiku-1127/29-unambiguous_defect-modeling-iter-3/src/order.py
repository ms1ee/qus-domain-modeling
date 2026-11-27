"""Order management: validation, rider assignment and order bookkeeping."""

import logging

import globalvar
from grid import MAP_SIZE, manhattan
from order_model import STATUS_COMPLETED, Order

logger = logging.getLogger(__name__)


class OrderValidationError(ValueError):
    """Raised when order input is malformed or cannot be served."""


def find_best_rider_for_order(order):
    """Select the most suitable rider for an order.

    The score is the Manhattan distance from the rider's current position to
    the restaurant plus a load penalty per already assigned order. Riders that
    already hold the maximum number of orders are skipped. Ties are broken by
    the lower rider id.

    Args:
        order: The Order that needs a rider.

    Returns:
        Rider: The best available rider, or None if no rider has capacity.
    """
    riders = globalvar.get_value("riders") or []
    capacity = int(globalvar.get_value("rider_capacity", 2))
    penalty = int(globalvar.get_value("load_penalty", 150))

    best = None
    best_score = None
    for rider in riders:
        if len(rider.orders) >= capacity:
            continue
        distance = manhattan(rider.position, order.restaurant_pos)
        score = distance + penalty * len(rider.orders)
        if (best is None or score < best_score
                or (score == best_score and rider.rider_id < best.rider_id)):
            best = rider
            best_score = score
    return best


def _parse_coordinate(value, label):
    """Validate a single coordinate value.

    Args:
        value: int or numeric string.
        label: Human-readable name used in error messages.

    Returns:
        int: The validated coordinate.

    Raises:
        OrderValidationError: If the value is not an integer in range.
    """
    if isinstance(value, bool):
        raise OrderValidationError("%s must be an integer, got %r" % (label, value))
    if isinstance(value, int):
        number = value
    elif isinstance(value, str):
        try:
            number = int(value.strip())
        except ValueError:
            raise OrderValidationError("%s must be an integer, got %r" % (label, value))
    else:
        raise OrderValidationError("%s must be an integer, got %r" % (label, value))
    if not 0 <= number <= MAP_SIZE:
        raise OrderValidationError("%s must be within 0-%d, got %d"
                                   % (label, MAP_SIZE, number))
    return number


def validate_point(point, label):
    """Validate an (x, y) location supplied by the user.

    Args:
        point: Sequence of two coordinates.
        label: Name used in error messages, e.g. "Restaurant".

    Returns:
        tuple[int, int]: Validated coordinates.

    Raises:
        OrderValidationError: If the point is malformed or out of range.
    """
    if point is None or len(point) != 2:
        raise OrderValidationError("%s needs exactly two coordinates" % label)
    x = _parse_coordinate(point[0], label + " x")
    y = _parse_coordinate(point[1], label + " y")
    return x, y


class OrderManager:
    """Creates, assigns and tracks orders.

    All orders are kept in the global ``"orders"`` list.
    """

    @property
    def orders(self):
        """Return the list of all orders (active and completed)."""
        orders = globalvar.get_value("orders")
        if orders is None:
            orders = []
            globalvar.set_value("orders", orders)
        return orders

    def create_order(self, restaurant, customer):
        """Validate input coordinates and create a new order.

        Args:
            restaurant: Restaurant (x, y) in 0-800.
            customer: Customer (x, y) in 0-800.

        Returns:
            Order: The newly created, unassigned order.

        Raises:
            OrderValidationError: If the coordinates are invalid.
        """
        res = validate_point(restaurant, "Restaurant")
        cus = validate_point(customer, "Customer")
        order = Order(res, cus)
        self.orders.append(order)
        logger.info("order %s created: restaurant=%r customer=%r",
                    order.id, order.restaurant_pos, order.customer_pos)
        return order

    def cancel_order(self, order):
        """Remove an order that could not be assigned.

        Args:
            order: The order to remove.
        """
        if order in self.orders:
            self.orders.remove(order)

    def assign(self, order, rider):
        """Assign an order to a rider by appending it to the rider's list.

        Args:
            order: The order to assign.
            rider: The rider receiving the order.
        """
        rider.orders.append(order)
        order.assign_to(rider.rider_id)
        logger.info("order %s assigned to rider %s", order.id, rider.rider_id)

    def active_orders(self):
        """Return orders that are not yet completed."""
        return [order for order in self.orders if order.status != STATUS_COMPLETED]

    def completed_orders(self):
        """Return orders that have been delivered."""
        return [order for order in self.orders if order.status == STATUS_COMPLETED]
