"""Order creation, tracking and rider assignment logic."""

import logging
from typing import List, Optional

import globalvar
from order_model import Order
from path_planner import manhattan

LOGGER = logging.getLogger(__name__)

LOAD_PENALTY = 200  # Extra distance units charged per order already held.


class OrderManager:
    """Creates orders and keeps track of every order in the system."""

    def create_order(self, res_x: int, res_y: int, cus_x: int, cus_y: int) -> Order:
        """Validate coordinates, create an order and store it globally.

        Args:
            res_x: Restaurant x coordinate (0-800).
            res_y: Restaurant y coordinate (0-800).
            cus_x: Customer x coordinate (0-800).
            cus_y: Customer y coordinate (0-800).

        Returns:
            The newly created Order.

        Raises:
            ValueError: If any coordinate is invalid.
        """
        order = Order((res_x, res_y), (cus_x, cus_y))
        globalvar.get_value("orders").append(order)
        LOGGER.info("created order %s", order.id)
        return order

    def all_orders(self) -> List[Order]:
        """Return every order ever created, in creation order."""
        return list(globalvar.get_value("orders", []))

    def active_orders(self) -> List[Order]:
        """Return orders that are not yet completed."""
        return [o for o in self.all_orders() if o.status != "completed"]

    def completed_orders(self) -> List[Order]:
        """Return completed orders."""
        return [o for o in self.all_orders() if o.status == "completed"]


def find_best_rider_for_order(order: Order) -> Optional[Order]:
    """Choose the best rider for an order (closest rider first, load-balanced).

    Each rider is scored by its Manhattan distance to the restaurant plus a
    penalty of ``LOAD_PENALTY`` per order it already holds. The lowest score
    wins; ties are broken by the lower rider ID.

    Args:
        order: The order needing a rider.

    Returns:
        The selected Rider, or None when no riders exist.
    """
    riders = globalvar.get_value("riders", [])
    best = None
    best_key = None
    for rider in riders:
        distance = manhattan(rider.position, order.res_pos)
        score = distance + LOAD_PENALTY * len(rider.orders)
        key = (score, rider.rider_id)
        if best_key is None or key < best_key:
            best = rider
            best_key = key
    if best is None:
        LOGGER.warning("no rider available for order %s", order.id)
    return best
