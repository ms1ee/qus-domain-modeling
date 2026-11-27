"""Order management: creation, rider assignment and cancellation."""

import logging
from typing import TYPE_CHECKING, Optional

from config import LOAD_PENALTY
from globalvar import get_value
from order_model import Order
from path_planner import manhattan

if TYPE_CHECKING:  # pragma: no cover
    from rider import Rider

LOGGER = logging.getLogger("dispatch.order")


def find_best_rider_for_order(order) -> Optional["Rider"]:
    """Select the best rider for an order.

    Each rider is scored by its Manhattan distance to the restaurant plus a
    load penalty per already-assigned order. The lowest score wins, which
    favours the closest rider while balancing load between riders. Ties are
    broken by the lower rider ID.

    Args:
        order: The order needing a rider.

    Returns:
        Rider | None: The chosen rider, or None if no riders exist.
    """
    riders = get_value("riders", []) or []
    best = None
    best_key = None
    for rider in riders:
        distance = manhattan((rider.x, rider.y), order.restaurant)
        key = (distance + LOAD_PENALTY * len(rider.orders), rider.rider_id)
        if best_key is None or key < best_key:
            best, best_key = rider, key
    return best


class OrderManager:
    """Creates, assigns and tracks orders.

    Attributes:
        orders: All orders created in this session, in creation order.
    """

    def __init__(self):
        """Create an empty order manager."""
        self.orders = []

    def create_order(self, res_pos, cus_pos, tick: int = 0) -> Order:
        """Create and register a new order.

        Args:
            res_pos: Restaurant coordinates ``[x, y]``.
            cus_pos: Customer coordinates ``[x, y]``.
            tick: Current simulation tick (recorded as start time).

        Returns:
            Order: The newly created order.

        Raises:
            ValueError: If coordinates are invalid.
        """
        order = Order(res_pos, cus_pos)
        order.start_time = int(tick)
        self.orders.append(order)
        return order

    def assign_order(self, order: Order) -> Optional["Rider"]:
        """Assign an order to the best available rider.

        Args:
            order: The order to assign.

        Returns:
            Rider | None: The rider now holding the order, or None if no
            rider is available.
        """
        rider = find_best_rider_for_order(order)
        if rider is None:
            LOGGER.warning("No rider available for order %s", order.id)
            return None
        order.assign_to(rider.rider_id)
        rider.orders.append(order)
        LOGGER.info("Order %s assigned to rider %s", order.id, rider.rider_id)
        return rider

    def cancel_order(self, order: Order) -> None:
        """Remove an order from the manager and from its rider, if assigned.

        Args:
            order: The order to cancel.
        """
        if order in self.orders:
            self.orders.remove(order)
        if order.rider_id is not None:
            for rider in get_value("riders", []) or []:
                if rider.rider_id == order.rider_id and order in rider.orders:
                    rider.orders.remove(order)

    def active_orders(self) -> list:
        """Return orders that have not yet been completed.

        Returns:
            list[Order]: Orders whose status is not "completed".
        """
        return [o for o in self.orders if o.status != "completed"]

    def completed_orders(self) -> list:
        """Return completed orders.

        Returns:
            list[Order]: Orders whose status is "completed".
        """
        return [o for o in self.orders if o.status == "completed"]
