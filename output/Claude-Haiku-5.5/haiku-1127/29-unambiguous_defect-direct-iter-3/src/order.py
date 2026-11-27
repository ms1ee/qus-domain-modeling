"""Order management: creation, rider matching and assignment.

``find_best_rider_for_order`` implements the distance-first strategy with a
load-balancing penalty: the score of a rider is its Manhattan distance to the
restaurant plus a fixed penalty per already-assigned order.
"""

import logging

import config
import globalvar
import grid
from order_model import STATUS_CREATED, Order

logger = logging.getLogger("dispatch.order")


class NoRiderAvailableError(RuntimeError):
    """Raised when no rider can accept a new order."""


def find_best_rider_for_order(order):
    """Return the most suitable rider for ``order``.

    Riders already at ``MAX_ORDERS_PER_RIDER`` are skipped. The score is
    ``manhattan(rider, restaurant_node) + LOAD_PENALTY * active_orders``;
    ties are broken by the lower rider ID.

    Args:
        order: Order to be assigned.

    Returns:
        Rider | None: The selected rider, or None if no rider has capacity.
    """
    riders = globalvar.get_value("riders", [])
    best_rider = None
    best_key = None
    for rider in riders:
        load = len(rider.orders)
        if load >= config.MAX_ORDERS_PER_RIDER:
            continue
        distance = grid.manhattan(rider.position, order.restaurant_node)
        score = distance + config.LOAD_PENALTY * load
        key = (score, rider.rider_id)
        if best_key is None or key < best_key:
            best_key = key
            best_rider = rider
    return best_rider


class OrderManager:
    """Creates orders and assigns them to riders.

    Args:
        system_manager: The SystemManager used for recruitment decisions.
    """

    def __init__(self, system_manager):
        self._system = system_manager

    @staticmethod
    def parse_coordinates(values):
        """Validate ``[restaurant_x, restaurant_y, customer_x, customer_y]``.

        Args:
            values: Sequence of four integers.

        Returns:
            tuple[tuple[int, int], tuple[int, int]]: Restaurant and customer points.

        Raises:
            ValueError: If the sequence is malformed or out of range.
        """
        if len(values) != 4:
            raise ValueError("expected four integers: restaurant_x restaurant_y customer_x customer_y")
        for value in values:
            if isinstance(value, bool) or not isinstance(value, int):
                raise ValueError(f"coordinate {value!r} is not an integer")
            if not grid.is_valid_coordinate(value):
                raise ValueError(
                    f"coordinate {value} is out of range "
                    f"[{config.COORD_MIN}, {config.COORD_MAX}]"
                )
        return (values[0], values[1]), (values[2], values[3])

    def create_order(self, values):
        """Create an order from four integer coordinates.

        Args:
            values: ``[restaurant_x, restaurant_y, customer_x, customer_y]``.

        Returns:
            Order: A newly created order (not yet assigned).

        Raises:
            ValueError: If the coordinates are invalid.
        """
        restaurant, customer = self.parse_coordinates(values)
        return Order(restaurant, customer)

    def assign_order(self, order):
        """Assign ``order`` to the best rider, recruiting one if necessary.

        A new rider is recruited when no rider is idle and the system can
        afford and accommodate one. The order is appended to the chosen
        rider's ``orders`` list.

        Args:
            order: Order in the created state.

        Returns:
            tuple[Rider, bool]: The assigned rider and whether a new rider
            was recruited for this order.

        Raises:
            ValueError: If the order has already been assigned.
            NoRiderAvailableError: If no rider has spare capacity.
        """
        if order.status != STATUS_CREATED:
            raise ValueError(f"order {order.id} is already {order.status}")

        new_rider = False
        if not any(rider.is_idle for rider in self._riders()) and self._system.can_recruit():
            new_rider = self._system.recruit_rider() is not None

        rider = find_best_rider_for_order(order)
        if rider is None:
            raise NoRiderAvailableError("no rider has capacity for this order")

        rider.orders.append(order)
        order.assign_to(rider.rider_id)
        rider.refresh_state()

        orders = globalvar.get_value("orders")
        if orders is None:
            orders = []
            globalvar.set_value("orders", orders)
        orders.append(order)

        logger.info("Order %s assigned to rider %s", order.id, rider.rider_id)
        return rider, new_rider

    def all_orders(self):
        """Return every order accepted into the system.

        Returns:
            list[Order]: Copy of the global order list.
        """
        return list(globalvar.get_value("orders", []))

    def active_orders(self):
        """Return orders that are not yet completed.

        Returns:
            list[Order]: Assigned or in-progress orders.
        """
        return [o for o in self.all_orders() if o.status != "completed"]

    def completed_orders(self):
        """Return completed orders in completion order.

        Returns:
            list[Order]: Completed order history.
        """
        return list(globalvar.get_value("order_history", []))

    @staticmethod
    def _riders():
        """Return the current rider list."""
        return globalvar.get_value("riders", [])
