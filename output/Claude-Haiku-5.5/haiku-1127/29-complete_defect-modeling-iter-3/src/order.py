"""Order management: rider assignment and pending-order handling."""

import logging
from typing import List, Optional

from globalvar import get_value
from order_model import STATUS_PENDING, Order
from rider import Rider

logger = logging.getLogger(__name__)

LOAD_PENALTY = 100


def find_best_rider_for_order(order: Order) -> Optional[Rider]:
    """Select the best rider for an order.

    The primary criterion is the distance from the rider's current position
    to the restaurant (closest rider first). Each already-queued order adds
    a load penalty so that work is balanced across riders. Riders already at
    ``max_orders_per_rider`` are skipped.

    Args:
        order: The order to assign.

    Returns:
        The chosen :class:`Rider`, or None if no rider has spare capacity.
    """
    max_load = int(get_value("max_orders_per_rider", 3))
    rx, ry = order.res_center
    best: Optional[Rider] = None
    best_key = None
    for rider in get_value("riders") or []:
        load = len(rider.orders)
        if load >= max_load:
            continue
        distance = abs(rider.x - rx) + abs(rider.y - ry)
        key = (distance + LOAD_PENALTY * load, rider.rider_id)
        if best_key is None or key < best_key:
            best, best_key = rider, key
    return best


class OrderManager:
    """Creates, assigns and tracks orders."""

    def __init__(self) -> None:
        """Create an empty order manager."""
        self.orders: List[Order] = []

    def create_order(self, res_pos, cus_pos, tick: int) -> Order:
        """Create and register a new pending order.

        Args:
            res_pos: Restaurant ``[x, y]``.
            cus_pos: Customer ``[x, y]``.
            tick: Simulated time of creation.

        Returns:
            The new :class:`Order`.
        """
        order = Order(res_pos, cus_pos)
        order.start_time = tick
        self.orders.append(order)
        logger.info("Created order %s at tick %s", order.id, tick)
        return order

    def assign(self, order: Order) -> Optional[Rider]:
        """Assign an order to the best available rider.

        Args:
            order: Pending order to assign.

        Returns:
            The rider the order was given to, or None if none is available.
        """
        rider = find_best_rider_for_order(order)
        if rider is None:
            return None
        order.assign_to(rider.rider_id)
        rider.orders.append(order)
        logger.info("Order %s assigned to rider %s", order.id, rider.rider_id)
        return rider

    def retry_pending(self) -> List[Order]:
        """Try to assign every pending order.

        Returns:
            Orders that were assigned during this call.
        """
        assigned: List[Order] = []
        for order in self.pending_orders():
            if self.assign(order) is not None:
                assigned.append(order)
        return assigned

    def pending_orders(self) -> List[Order]:
        """Return orders that still wait for a rider."""
        return [o for o in self.orders if o.status == STATUS_PENDING]

    def active_orders(self) -> List[Order]:
        """Return orders that are not yet completed."""
        return [o for o in self.orders if o.status != "completed"]

    def get_order(self, order_id: int) -> Optional[Order]:
        """Look up an order by identifier.

        Args:
            order_id: Order identifier.

        Returns:
            The matching order, or None.
        """
        for order in self.orders:
            if order.id == order_id:
                return order
        return None
