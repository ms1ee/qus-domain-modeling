"""Order assignment and order management.

Assignment strategy: the closest available rider is preferred. A load
penalty is added per already-assigned order so that work is balanced across
riders. Riders already at their order capacity are skipped.
"""

import logging
from typing import List, Optional

import globalvar
from order_model import Order
from path_planner import manhattan
from rider import Rider

LOAD_PENALTY = 200

logger = logging.getLogger("dispatch.order")


def _max_orders_per_rider() -> int:
    """Return the configured per-rider order capacity."""
    config = globalvar.get_value("config") or {}
    return int(config.get("max_orders_per_rider", 3))


def find_best_rider_for_order(order: Order) -> Optional[Rider]:
    """Choose the best rider for an order.

    Score = Manhattan distance from the rider to the restaurant plus
    ``LOAD_PENALTY`` times the number of orders the rider already holds.
    The lowest score wins; ties go to the lower rider ID.

    Args:
        order: The order needing a rider.

    Returns:
        The chosen Rider, or None when no rider has spare capacity.
    """
    riders = globalvar.get_value("riders", []) or []
    capacity = _max_orders_per_rider()
    best: Optional[Rider] = None
    best_score: Optional[int] = None
    for rider in riders:
        if len(rider.orders) >= capacity:
            continue
        distance = manhattan(rider.position, order.res_pos)
        score = distance + LOAD_PENALTY * len(rider.orders)
        if (best is None or score < best_score or
                (score == best_score and rider.rider_id < best.rider_id)):
            best = rider
            best_score = score
    return best


class OrderManager:
    """Creates, assigns and tracks orders.

    All orders are stored in the global ``"orders"`` list.
    """

    def create_order(self, restaurant_pos, customer_pos) -> Order:
        """Create an order and register it in the global order list.

        Args:
            restaurant_pos: ``(x, y)`` restaurant coordinates.
            customer_pos: ``(x, y)`` customer coordinates.

        Returns:
            The newly created Order.
        """
        order = Order(restaurant_pos, customer_pos)
        orders = globalvar.get_value("orders")
        orders.append(order)
        logger.info("Created order %s", order.id)
        return order

    def assign_order(self, order: Order) -> Optional[Rider]:
        """Assign an order to the best available rider.

        Args:
            order: Order to assign.

        Returns:
            The rider the order was assigned to, or None if none is free.
        """
        rider = find_best_rider_for_order(order)
        if rider is None:
            logger.info("No rider available for order %s", order.id)
            return None
        order.assign_to(rider.rider_id)
        rider.orders.append(order)
        logger.info("Assigned order %s to rider %s", order.id, rider.rider_id)
        return rider

    def assign_pending_orders(self) -> List[Order]:
        """Try to assign every pending order, oldest first.

        Returns:
            Orders that were assigned during this call.
        """
        assigned: List[Order] = []
        for order in list(globalvar.get_value("orders", []) or []):
            if order.status != "pending":
                continue
            if self.assign_order(order) is not None:
                assigned.append(order)
        return assigned

    def pending_orders(self) -> List[Order]:
        """Return orders that are still waiting for a rider."""
        return [o for o in globalvar.get_value("orders", []) or []
                if o.status == "pending"]

    def completed_orders(self) -> List[Order]:
        """Return orders that have been delivered."""
        return [o for o in globalvar.get_value("orders", []) or []
                if o.status == "completed"]
