"""Order management: creation, distance-first assignment and completion.

``find_best_rider_for_order`` implements the assignment strategy: the closest
rider is preferred, with a penalty per active order so that work is spread
across riders (load balancing).
"""

import logging
from typing import List, Optional, Sequence

import globalvar
from order_model import Order
from pathplanner import manhattan, validate_coordinate
from rider import Rider

logger = logging.getLogger(__name__)

DEFAULT_LOAD_PENALTY = 200
DEFAULT_ORDER_FEE = 150


def _param(name: str, default: int) -> int:
    """Read a system parameter with a fallback default.

    Args:
        name: Parameter name.
        default: Value used when the parameter is missing.

    Returns:
        The parameter value.
    """
    params = globalvar.get_value("params", {}) or {}
    return params.get(name, default)


def find_best_rider_for_order(order: Order) -> Optional[Rider]:
    """Select the best rider for an order.

    The score of each rider is ``distance_to_restaurant + load * penalty``,
    where ``load`` is the number of orders the rider already holds. The rider
    with the lowest score wins; ties go to the lower rider ID.

    Args:
        order: The order that needs a rider.

    Returns:
        The selected Rider, or None if no riders exist.
    """
    riders = globalvar.get_value("riders", []) or []
    if not riders:
        return None
    penalty = _param("load_penalty", DEFAULT_LOAD_PENALTY)
    best: Optional[Rider] = None
    best_key = None
    for rider in riders:
        distance = manhattan(rider.position(), order.res_center)
        load = len(rider.orders)
        key = (distance + load * penalty, rider.rider_id)
        if best_key is None or key < best_key:
            best_key = key
            best = rider
    return best


class OrderManager:
    """Creates, assigns and tracks orders."""

    def create_order(self, coords: Sequence[object]) -> Order:
        """Create an order from ``[restaurant_x, restaurant_y, customer_x, customer_y]``.

        The order fee is credited to the system funds and the order is added
        to the order history.

        Args:
            coords: Four integer coordinates in range 0-800.

        Returns:
            The newly created Order.

        Raises:
            ValueError: If the count or values of coordinates are invalid.
        """
        if len(coords) != 4:
            raise ValueError("an order needs exactly four coordinates")
        rx, ry, cx, cy = (validate_coordinate(value) for value in coords)
        order = Order((rx, ry), (cx, cy))
        order.start_tick = globalvar.get_value("tick", 0) or 0
        globalvar.get_value("orders").append(order)
        globalvar.set_value("funds", globalvar.get_value("funds", 0) + _param("order_fee", DEFAULT_ORDER_FEE))
        logger.info("Order %s created: restaurant=%s customer=%s",
                    order.id, order.res_pos, order.cus_pos)
        return order

    def assign_order(self, order: Order) -> Optional[Rider]:
        """Assign an order to the best available rider.

        If no rider exists the order is placed in the pending queue.

        Args:
            order: The order to assign.

        Returns:
            The rider that received the order, or None if it is pending.
        """
        rider = find_best_rider_for_order(order)
        if rider is None:
            if order not in globalvar.get_value("pending_orders"):
                globalvar.get_value("pending_orders").append(order)
            logger.warning("No rider available; order %s is pending", order.id)
            return None
        rider.orders.append(order)
        order.assign_to(rider.rider_id)
        logger.info("Order %s assigned to rider %s", order.id, rider.rider_id)
        return rider

    def process_pending(self) -> List[Rider]:
        """Try to assign every pending order.

        Returns:
            List of riders that received a previously pending order.
        """
        pending = globalvar.get_value("pending_orders")
        waiting = list(pending)
        pending.clear()
        assigned: List[Rider] = []
        for order in waiting:
            rider = self.assign_order(order)
            if rider is not None:
                assigned.append(rider)
        return assigned

    @property
    def pending_count(self) -> int:
        """Return the number of orders waiting for a rider."""
        return len(globalvar.get_value("pending_orders", []) or [])
