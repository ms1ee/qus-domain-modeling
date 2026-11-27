"""Order management: creation, validation, and rider assignment."""

import logging
from typing import List, Optional

import globalvar
from config import INPUT_MAX, INPUT_MIN
from order_model import Order
from path_planner import PathPlanner
from rider import Rider

logger = logging.getLogger("dispatch.order")


def find_best_rider_for_order(order: Order) -> Optional[Rider]:
    """Select the best rider for an order.

    Selection rule:
      1. Fewest current active orders (the assignment always goes to the
         least-loaded rider).
      2. Ties are broken by the Euclidean distance
         ``sqrt((rider_x - restaurant_x)^2 + (rider_y - restaurant_y)^2)``,
         so the closest rider wins.

    Args:
        order: The order needing a rider.

    Returns:
        The chosen rider, or None if no riders exist.
    """
    riders = globalvar.get_value("riders") or []
    if not riders:
        return None

    def sort_key(rider: Rider):
        distance = PathPlanner.euclidean(rider.position, order.res_pos)
        return len(rider.active_orders()), distance

    return min(riders, key=sort_key)


class OrderManager:
    """Creates, tracks and assigns orders."""

    @staticmethod
    def validate_coordinate(value: int) -> int:
        """Validate a single input coordinate.

        Args:
            value: Integer coordinate.

        Returns:
            The validated coordinate.

        Raises:
            ValueError: If the value is not an int or is out of range.
        """
        if isinstance(value, bool) or not isinstance(value, int):
            raise ValueError("coordinates must be integers")
        if value < INPUT_MIN or value > INPUT_MAX:
            raise ValueError(f"coordinate {value} is outside {INPUT_MIN}-{INPUT_MAX}")
        return value

    def create_order(self, res_x: int, res_y: int, cus_x: int, cus_y: int) -> Order:
        """Validate coordinates, create an order and register it.

        Args:
            res_x: Restaurant x coordinate.
            res_y: Restaurant y coordinate.
            cus_x: Customer x coordinate.
            cus_y: Customer y coordinate.

        Returns:
            The newly created order (status ``"created"``).

        Raises:
            ValueError: If any coordinate is invalid.
        """
        values = [self.validate_coordinate(v) for v in (res_x, res_y, cus_x, cus_y)]
        order = Order((values[0], values[1]), (values[2], values[3]))
        globalvar.get_value("orders").append(order)
        logger.info("Created order %s", order.id)
        return order

    @staticmethod
    def list_orders() -> List[Order]:
        """Return all orders ever created, oldest first."""
        return list(globalvar.get_value("orders") or [])

    def pending_orders(self) -> List[Order]:
        """Return orders that have not been assigned to a rider yet."""
        return [o for o in self.list_orders() if o.status == "created"]

    def assign_order(self, order: Order) -> Optional[Rider]:
        """Assign an order to the best rider.

        The order is recorded on the rider by appending it to ``rider.orders``
        and calling ``order.assign_to``. The rider accepts it on its next tick.

        Args:
            order: The order to assign.

        Returns:
            The rider the order was assigned to, or None if no rider exists.
        """
        rider = find_best_rider_for_order(order)
        if rider is None:
            logger.warning("No rider available for order %s", order.id)
            return None
        order.assign_to(rider.rider_id)
        rider.orders.append(order)
        logger.info("Order %s assigned to rider %s", order.id, rider.rider_id)
        return rider
