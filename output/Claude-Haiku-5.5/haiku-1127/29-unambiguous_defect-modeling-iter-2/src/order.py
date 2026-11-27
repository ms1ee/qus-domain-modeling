"""Order management and distance-first rider assignment."""

import logging
from typing import Any, Dict, List, Optional

from globalvar import get_value
from grid_map import manhattan
from order_model import Order

logger = logging.getLogger(__name__)

# Load-balancing penalty (in distance units) added per order already held.
LOAD_PENALTY = 150
DEFAULT_MAX_RIDER_LOAD = 3


class OrderManager:
    """Creates, assigns, and tracks orders.

    Orders are stored in the global variable ``orders``; completed orders
    are additionally recorded in ``order_history`` by the rider on delivery.
    """

    @property
    def orderIdCounter(self) -> int:
        """int: Last issued order id."""
        return int(get_value("order_id_counter", 0) or 0)

    def create_order(self, res_pos, cus_pos) -> Order:
        """Create an order from restaurant and customer coordinates.

        Args:
            res_pos (Sequence[int]): Restaurant ``[x, y]``.
            cus_pos (Sequence[int]): Customer ``[x, y]``.

        Returns:
            Order: The newly created order (already stored globally).
        """
        order = Order(res_pos, cus_pos)
        get_value("orders").append(order)
        return order

    def discard_order(self, order: Order) -> None:
        """Remove an order that could not be dispatched.

        Args:
            order (Order): Order to remove from the global order list.
        """
        orders = get_value("orders")
        if order in orders:
            orders.remove(order)
            logger.info("Discarded undispatched order %s", order.id)

    def assign_order(self, order: Order, rider) -> None:
        """Assign an order to a rider.

        Args:
            order (Order): Order to assign.
            rider (Rider): Rider receiving the order.
        """
        order.assign_to(rider.rider_id)
        rider.accept_order(order)
        logger.info("Order %s assigned to rider %s", order.id, rider.rider_id)

    def active_orders(self) -> List[Order]:
        """Return all orders that are not yet completed.

        Returns:
            list[Order]: Active orders in creation order.
        """
        return [o for o in get_value("orders", []) if o.is_active]

    def all_orders(self) -> List[Order]:
        """Return every order created in this session.

        Returns:
            list[Order]: All orders in creation order.
        """
        return list(get_value("orders", []))

    def completed_orders(self) -> List[Order]:
        """Return completed orders in completion order.

        Returns:
            list[Order]: Delivered orders.
        """
        return list(get_value("order_history", []))

    def to_dict_list(self) -> List[Dict[str, Any]]:
        """Serialise all orders.

        Returns:
            list[dict]: JSON-compatible order records.
        """
        return [o.to_dict() for o in self.all_orders()]


def find_best_rider_for_order(order: Order) -> Optional["Rider"]:
    """Select the best rider for an order using a distance-first rule.

    Each rider with spare capacity is scored by::

        score = manhattan(rider position, restaurant) + LOAD_PENALTY * load

    The lowest score wins, which keeps dispatch close to the restaurant while
    balancing load between riders. Ties are broken by rider id.

    Args:
        order (Order): Order that needs a rider.

    Returns:
        Rider | None: The chosen rider, or None if no rider has spare
        capacity (the caller may then recruit a new rider).
    """
    riders = get_value("riders", []) or []
    max_load = int(get_value("max_rider_load", DEFAULT_MAX_RIDER_LOAD)
                   or DEFAULT_MAX_RIDER_LOAD)
    best = None
    best_key = None
    for rider in riders:
        load = len(rider.orders)
        if load >= max_load:
            continue
        distance = manhattan(rider.position, order.res_pos)
        key = (distance + LOAD_PENALTY * load, rider.rider_id)
        if best_key is None or key < best_key:
            best = rider
            best_key = key
    return best
