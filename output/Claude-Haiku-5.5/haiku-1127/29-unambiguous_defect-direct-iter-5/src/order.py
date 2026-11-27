"""Order management: input validation, rider assignment, and completion accounting."""

import logging
from typing import TYPE_CHECKING, List, Sequence

from globalvar import get_value, set_value
from order_model import STATUS_COMPLETED, Order
from path_planner import MAP_SIZE, manhattan

if TYPE_CHECKING:
    from rider import Rider

logger = logging.getLogger(__name__)

# Extra distance-equivalent cost added per active order a rider already holds.
# This spreads load across riders instead of overloading the closest one.
LOAD_PENALTY = 300


class NoRiderAvailableError(RuntimeError):
    """Raised when no rider exists and none can be recruited."""


def validate_coordinates(values: Sequence[object]) -> List[int]:
    """Validate the four order coordinates.

    Args:
        values: Sequence ``[restaurant_x, restaurant_y, customer_x, customer_y]``.

    Returns:
        A list of four integers.

    Raises:
        ValueError: If the count is wrong, a value is not an integer, or a
            value lies outside 0-800.
    """
    if len(values) != 4:
        raise ValueError(f"expected 4 coordinates, got {len(values)}")
    result: List[int] = []
    for value in values:
        if isinstance(value, bool) or not isinstance(value, int):
            raise ValueError(f"coordinate {value!r} is not an integer")
        if not 0 <= value <= MAP_SIZE:
            raise ValueError(f"coordinate {value} is outside the range 0-{MAP_SIZE}")
        result.append(value)
    return result


def find_best_rider_for_order(order: Order) -> "Rider":
    """Select the most suitable rider for an order.

    The cost of a rider is the Manhattan distance from its current position to
    the restaurant plus ``LOAD_PENALTY`` for each order it already holds. The
    rider with the lowest cost wins, and ties go to the lower rider ID. If no
    rider exists, one is recruited when funds allow.

    Args:
        order: Order that needs a rider.

    Returns:
        The selected Rider.

    Raises:
        NoRiderAvailableError: If no rider exists and recruitment fails.
    """
    from system import recruit_rider  # local import avoids a circular dependency

    riders = get_value("riders", [])
    if not riders:
        if recruit_rider() is None:
            raise NoRiderAvailableError("no riders available and recruitment failed")
        riders = get_value("riders", [])

    best = None
    best_key = None
    for rider in riders:
        distance = manhattan(rider.position(), order.res_pos)
        key = (distance + LOAD_PENALTY * len(rider.orders), rider.rider_id)
        if best_key is None or key < best_key:
            best = rider
            best_key = key
    if best is None:
        raise NoRiderAvailableError("no rider could be selected")
    return best


def record_completion(order: Order) -> None:
    """Record a delivered order and credit the delivery fee to system funds.

    Args:
        order: The order that has just been delivered.
    """
    config = get_value("config", {})
    fee = int(config.get("delivery_fee", 0))
    set_value("funds", int(get_value("funds", 0)) + fee)
    get_value("completed_orders", []).append(order)
    logger.info(
        "Order %s completed by rider %s in %s ticks",
        order.id,
        order.rider_id,
        order.time_taken,
    )


class OrderManager:
    """Creates, assigns, and tracks orders."""

    def create_order(self, coordinates: Sequence[object]) -> Order:
        """Validate coordinates and create a new order.

        Args:
            coordinates: ``[restaurant_x, restaurant_y, customer_x, customer_y]``.

        Returns:
            The newly created Order, which is also stored in the global order list.

        Raises:
            ValueError: If the coordinates are invalid.
        """
        values = validate_coordinates(coordinates)
        order = Order(values[:2], values[2:])
        get_value("orders", []).append(order)
        logger.info("Created order %s: %s", order.id, order.to_list())
        return order

    def assign_order(self, order: Order) -> "Rider":
        """Assign an order to the best rider and append it to that rider's list.

        Args:
            order: Order to assign.

        Returns:
            The rider that received the order.
        """
        rider = find_best_rider_for_order(order)
        rider.orders.append(order)
        order.assign_to(rider.rider_id)
        logger.info("Order %s assigned to rider %s", order.id, rider.rider_id)
        return rider

    def discard_order(self, order: Order) -> None:
        """Remove an order from the global list, used when assignment fails.

        Args:
            order: Order to remove.
        """
        orders = get_value("orders", [])
        if order in orders:
            orders.remove(order)

    def active_orders(self) -> List[Order]:
        """Return all orders that are not yet completed."""
        return [o for o in get_value("orders", []) if o.status != STATUS_COMPLETED]

    def all_orders(self) -> List[Order]:
        """Return every order created in this session."""
        return list(get_value("orders", []))
