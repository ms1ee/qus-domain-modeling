"""Order management and the closest-rider assignment algorithm.

Assignment picks the rider with the smallest score, where the score is the
Manhattan distance from the rider to the restaurant plus a load penalty per
order already held by that rider. This keeps the distance-first strategy
while balancing load between riders.
"""

import logging
from typing import Any, List, Optional, Sequence

import globalvar
from order_model import Order

logger = logging.getLogger(__name__)

DEFAULT_LOAD_PENALTY = 100


def find_best_rider_for_order(order: Order,
                              load_penalty: int = DEFAULT_LOAD_PENALTY
                              ) -> Optional[Any]:
    """Find the best rider for an order.

    Args:
        order: The order to assign.
        load_penalty: Score added per order already held by a rider.

    Returns:
        The selected Rider, or None if no riders exist.
    """
    riders = globalvar.get_value("riders") or []
    best = None
    best_key = None
    rx, ry = order.restaurant_pos
    for rider in riders:
        distance = abs(rider.x - rx) + abs(rider.y - ry)
        key = (distance + load_penalty * len(rider.orders), rider.rider_id)
        if best_key is None or key < best_key:
            best = rider
            best_key = key
    return best


class OrderManager:
    """Creates, assigns and tracks orders.

    Attributes:
        order_counter: Number of orders created so far.
        orders: History of all orders.
        pending: Orders waiting for a rider.
        load_penalty: Load-balancing penalty used by the assignment.
    """

    def __init__(self, load_penalty: int = DEFAULT_LOAD_PENALTY) -> None:
        """Create an empty order manager.

        Args:
            load_penalty: Load-balancing penalty for rider selection.
        """
        self.order_counter = 0
        self.orders: List[Order] = []
        self.pending: List[Order] = []
        self.load_penalty = int(load_penalty)

    def create_order(self, res_pos: Sequence[int], cus_pos: Sequence[int],
                     tick: int = 0) -> Order:
        """Create and register a new order.

        Args:
            res_pos: Restaurant (x, y), 0-800.
            cus_pos: Customer (x, y), 0-800.
            tick: Current simulated tick.

        Returns:
            The created Order.

        Raises:
            ValueError: If a coordinate is invalid.
        """
        order = Order(res_pos, cus_pos, start_time=tick)
        self.order_counter += 1
        self.orders.append(order)
        logger.info("Created order %d at tick %d", order.id, tick)
        return order

    def _bind(self, order: Order, rider: Any) -> None:
        """Attach an order to a rider."""
        order.assign_to(rider.rider_id)
        rider.orders.append(order)
        if order in self.pending:
            self.pending.remove(order)
        logger.info("Order %d assigned to rider %d", order.id, rider.rider_id)

    def assign_order(self, order: Order) -> Optional[Any]:
        """Assign an order to the best available rider.

        If no rider exists, the order is queued as pending.

        Args:
            order: A pending order.

        Returns:
            The assigned Rider, or None if the order is pending.

        Raises:
            RuntimeError: If the order has already been assigned.
        """
        if order.status != Order.PENDING:
            raise RuntimeError(
                f"Order {order.id} cannot be assigned from status "
                f"'{order.status}'")
        rider = find_best_rider_for_order(order, self.load_penalty)
        if rider is None:
            if order not in self.pending:
                self.pending.append(order)
            logger.warning("No rider available; order %d is pending", order.id)
            return None
        self._bind(order, rider)
        return rider

    def try_assign_pending(self) -> int:
        """Try to assign every pending order.

        Returns:
            Number of orders assigned in this call.
        """
        assigned = 0
        for order in list(self.pending):
            rider = find_best_rider_for_order(order, self.load_penalty)
            if rider is None:
                break
            self._bind(order, rider)
            assigned += 1
        return assigned

    def active_orders(self) -> List[Order]:
        """Return orders that are not yet completed."""
        return [o for o in self.orders if o.status != Order.COMPLETED]

    def get_order(self, order_id: int) -> Optional[Order]:
        """Return the order with the given id, or None."""
        for order in self.orders:
            if order.id == order_id:
                return order
        return None
