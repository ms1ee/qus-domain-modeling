"""Order management: coordinate conversion, creation and assignment.

Provides :func:`find_best_rider_for_order` (distance-first assignment) and
:class:`OrderManager`.
"""

import logging
import math

import globalvar
from config import SETTINGS
from order_model import (
    Order,
    STATUS_COMPLETED,
    STATUS_PENDING,
)

logger = logging.getLogger(__name__)


def find_best_rider_for_order(order):
    """Find the rider closest to the order's restaurant.

    The distance is Euclidean: ``sqrt((rx - res_x)^2 + (ry - res_y)^2)``.
    Ties are broken by the smaller current workload and then by rider ID, which
    spreads load among equally placed riders.

    Args:
        order: The Order to assign; its ``res_pos`` is used.

    Returns:
        Rider: The best rider for the order.

    Raises:
        LookupError: If there are no riders.
    """
    riders = globalvar.get_value("riders") or []
    if not riders:
        raise LookupError("No riders are available to take this order.")
    res_x, res_y = order.res_pos

    def sort_key(rider):
        distance = math.hypot(rider.x - res_x, rider.y - res_y)
        return (distance, len(rider.orders), rider.rider_id)

    return min(riders, key=sort_key)


class OrderManager:
    """Creates, tracks and assigns orders."""

    @staticmethod
    def to_cell_center(value):
        """Convert a raw coordinate to the centre of its grid cell.

        Uses ``center = (value // 100) * 100 + 50``; values equal to the map
        size are mapped into the last cell.

        Args:
            value: Integer coordinate in the range 0-800.

        Returns:
            int: The cell centre coordinate.

        Raises:
            ValueError: If the value is not an integer or out of range.
        """
        size = SETTINGS["map_size"]
        cell = SETTINGS["cell_size"]
        if not isinstance(value, int) or isinstance(value, bool):
            raise ValueError(f"Coordinate {value!r} must be an integer.")
        if value < 0 or value > size:
            raise ValueError(f"Coordinate {value} is outside the range 0-{size}.")
        index = min(value // cell, SETTINGS["grid_dim"] - 1)
        return index * cell + cell // 2

    def create_order(self, coords):
        """Create and register an order from four raw coordinates.

        Args:
            coords: ``[restaurant_x, restaurant_y, customer_x, customer_y]``.

        Returns:
            Order: The new pending order.

        Raises:
            ValueError: If the input is malformed or out of range.
        """
        if len(coords) != 4:
            raise ValueError("An order needs exactly four coordinates.")
        res_x, res_y, cus_x, cus_y = coords
        res_pos = (self.to_cell_center(res_x), self.to_cell_center(res_y))
        cus_pos = (self.to_cell_center(cus_x), self.to_cell_center(cus_y))
        order = Order(res_pos, cus_pos)
        globalvar.get_value("orders").append(order)
        logger.info("Created order #%d restaurant=%s customer=%s",
                    order.id, res_pos, cus_pos)
        return order

    def all_orders(self):
        """Return every order created in this session.

        Returns:
            list[Order]: A copy of the order list.
        """
        return list(globalvar.get_value("orders") or [])

    def pending_orders(self):
        """Return orders still waiting for assignment.

        Returns:
            list[Order]: Orders with status "pending".
        """
        return [o for o in self.all_orders() if o.status == STATUS_PENDING]

    def active_orders(self):
        """Return orders that are not yet completed.

        Returns:
            list[Order]: Orders whose status is not "completed".
        """
        return [o for o in self.all_orders() if o.status != STATUS_COMPLETED]

    def assign(self, order):
        """Assign an order to the closest rider and append it to that rider.

        Args:
            order: The Order to assign.

        Returns:
            Rider: The rider that received the order.

        Raises:
            LookupError: If no rider is available.
        """
        rider = find_best_rider_for_order(order)
        order.assign_to(rider.rider_id)
        rider.orders.append(order)
        logger.info("Order #%d assigned to rider #%d", order.id, rider.rider_id)
        return rider
