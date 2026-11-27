"""Order management and the closest-rider assignment strategy."""

import logging
from typing import Any, List, Optional

import globalvar
from order_model import Order
from path_planner import manhattan

logger = logging.getLogger(__name__)

# Extra distance-equivalent cost per already queued order (load balancing).
LOAD_PENALTY = 150


def find_best_rider_for_order(order: Order) -> Optional[Any]:
    """Select the rider that should receive ``order``.

    Strategy: closest rider first. Each candidate is scored by its Manhattan
    distance to the restaurant plus a load penalty per queued order, so that
    competing riders are balanced. Ties are broken by lower rider id.

    Args:
        order: The order to assign.

    Returns:
        The chosen Rider, or None if no riders exist.
    """
    riders = globalvar.get_value("riders") or []
    best = None
    best_key = None
    for rider in riders:
        distance = manhattan(rider.position, order.res_pos)
        key = (distance + LOAD_PENALTY * len(rider.orders), rider.rider_id)
        if best_key is None or key < best_key:
            best = rider
            best_key = key
    return best


class OrderManager:
    """Creates, assigns and tracks orders."""

    def create_order(self, res_pos, cus_pos) -> Order:
        """Create an order and add it to the order history.

        Args:
            res_pos: Restaurant coordinates (x, y).
            cus_pos: Customer coordinates (x, y).

        Returns:
            The newly created Order.
        """
        order = Order(res_pos, cus_pos)
        self.all_orders().append(order)
        logger.info("Order %d created", order.id)
        return order

    def assign_order(self, order: Order) -> Any:
        """Assign an order to the best available rider.

        Args:
            order: Pending order to assign.

        Returns:
            The Rider that received the order.

        Raises:
            RuntimeError: If no rider exists to take the order.
        """
        rider = find_best_rider_for_order(order)
        if rider is None:
            raise RuntimeError("No rider available for assignment")
        order.assign_to(rider.rider_id)
        rider.orders.append(order)
        rider.sync_state()
        logger.info("Order %d assigned to rider %d", order.id, rider.rider_id)
        return rider

    @staticmethod
    def all_orders() -> List[Order]:
        """Return the list of all orders ever created."""
        return globalvar.get_value("orders")

    def active_orders(self) -> List[Order]:
        """Return orders that have not yet been completed."""
        return [o for o in self.all_orders() if o.status != "completed"]

    def completed_orders(self) -> List[Order]:
        """Return orders that have been delivered."""
        return [o for o in self.all_orders() if o.status == "completed"]

    def get_order(self, order_id: int) -> Optional[Order]:
        """Look up an order by id."""
        for order in self.all_orders():
            if order.id == order_id:
                return order
        return None
