"""Order assignment and order lifecycle management.

``find_best_rider_for_order`` implements distance-first assignment using the
Euclidean distance from each rider to the restaurant. ``OrderManager`` keeps
the pending and historical order lists.
"""

import logging
import math
from typing import List, Optional

import config
import globalvar
from order_model import Order
from rider import Rider

logger = logging.getLogger(__name__)


def find_best_rider_for_order(order: Order) -> Optional[Rider]:
    """Select the closest rider that still has capacity for ``order``.

    Distance is ``sqrt((rider_x - restaurant_x)^2 + (rider_y - restaurant_y)^2)``.
    Riders already holding ``max_orders_per_rider`` orders are skipped, which
    balances load across riders. Ties are broken by fewer orders, then rider id.

    Args:
        order: The order to be assigned.

    Returns:
        The selected Rider, or None when no rider has spare capacity.
    """
    riders = globalvar.get_value("riders") or []
    capacity = int(config.CONFIG["max_orders_per_rider"])
    best: Optional[Rider] = None
    best_key = None
    for rider in riders:
        if len(rider.orders) >= capacity:
            continue
        distance = math.hypot(rider.x - order.restaurant_x, rider.y - order.restaurant_y)
        key = (distance, len(rider.orders), rider.rider_id)
        if best_key is None or key < best_key:
            best = rider
            best_key = key
    return best


class OrderManager:
    """Creates, assigns and tracks orders.

    Attributes:
        all_orders: Every order created in this session.
        pending_orders: Orders waiting for a rider.
    """

    def __init__(self) -> None:
        """Create an empty order manager."""
        self.all_orders: List[Order] = []
        self.pending_orders: List[Order] = []

    @property
    def pending_count(self) -> int:
        """Number of orders waiting for assignment."""
        return len(self.pending_orders)

    def create_order(self, res_pos, cus_pos) -> Order:
        """Create a new order stamped with the current tick and queue it.

        Args:
            res_pos: Restaurant point ``(x, y)``.
            cus_pos: Customer point ``(x, y)``.

        Returns:
            The created Order.
        """
        tick = globalvar.get_value("current_tick") or 0
        order = Order(res_pos, cus_pos, start_time=tick)
        self.all_orders.append(order)
        self.pending_orders.append(order)
        logger.info("order %s created at tick %s", order.id, tick)
        return order

    def assign_pending_orders(self) -> List[Order]:
        """Assign every pending order that can be matched to a rider.

        Returns:
            Orders assigned during this call.
        """
        assigned: List[Order] = []
        for order in list(self.pending_orders):
            rider = find_best_rider_for_order(order)
            if rider is None:
                continue
            order.assign_to(rider.rider_id)
            rider.orders.append(order)
            self.pending_orders.remove(order)
            assigned.append(order)
            logger.info("order %s assigned to rider %s", order.id, rider.rider_id)
        return assigned

    def active_orders(self) -> List[Order]:
        """Return orders that have not been completed yet.

        Returns:
            List of pending or assigned orders.
        """
        return [o for o in self.all_orders if o.status != "completed"]

    def completed_orders(self) -> List[Order]:
        """Return completed orders.

        Returns:
            List of completed orders.
        """
        return [o for o in self.all_orders if o.status == "completed"]
