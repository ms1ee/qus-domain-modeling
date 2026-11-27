"""Order management: creation, nearest-rider selection and assignment."""

import logging
import math
from typing import List, Optional

import globalvar
from order_model import STATUS_PENDING, Order
from rider import Rider

logger = logging.getLogger(__name__)

# Extra score added per order already queued on a rider. This balances load
# between riders while keeping the distance-first strategy dominant.
LOAD_PENALTY = 150.0


def find_best_rider_for_order(order: Order) -> Optional[Rider]:
    """Select the best rider for an order.

    The score of each rider is the Euclidean distance to the restaurant,
    ``sqrt((rider_x - restaurant_x)^2 + (rider_y - restaurant_y)^2)``, plus a
    load penalty for each order already assigned. The lowest score wins, so the
    closest rider is preferred while busy riders are only chosen when they are
    clearly closer or idle riders are unavailable.

    Args:
        order: The order needing a rider.

    Returns:
        The selected rider, or None if no riders exist.
    """
    riders = globalvar.get_value("riders", []) or []
    res_x, res_y = order.res_pos
    best: Optional[Rider] = None
    best_score = math.inf
    for rider in riders:
        distance = math.hypot(rider.x - res_x, rider.y - res_y)
        score = distance + LOAD_PENALTY * len(rider.orders)
        if score < best_score:
            best = rider
            best_score = score
    return best


class OrderManager:
    """Creates, tracks, and assigns orders."""

    def create_order(self, res_pos, cus_pos) -> Order:
        """Create an order and register it in the global order list.

        Args:
            res_pos: Restaurant coordinates ``[x, y]``.
            cus_pos: Customer coordinates ``[x, y]``.

        Returns:
            The newly created order.

        Raises:
            ValueError: If the coordinates are invalid.
        """
        order = Order(res_pos, cus_pos)
        orders = globalvar.get_value("orders")
        if orders is None:
            orders = []
            globalvar.set_value("orders", orders)
        orders.append(order)
        logger.info("Created order #%d", order.id)
        return order

    @staticmethod
    def all_orders() -> List[Order]:
        """Return every order created so far."""
        return list(globalvar.get_value("orders", []) or [])

    def pending_orders(self) -> List[Order]:
        """Return orders that have not yet been assigned to a rider."""
        return [o for o in self.all_orders() if o.status == STATUS_PENDING]

    def assign_order(self, order: Order) -> Optional[Rider]:
        """Assign an order to the best available rider.

        Args:
            order: The pending order to assign.

        Returns:
            The rider that received the order, or None if no rider exists.
        """
        rider = find_best_rider_for_order(order)
        if rider is None:
            logger.warning("No rider available for order #%d", order.id)
            return None
        order.assign_to(rider.rider_id)
        rider.orders.append(order)
        logger.info("Assigned order #%d to rider #%d", order.id, rider.rider_id)
        return rider
