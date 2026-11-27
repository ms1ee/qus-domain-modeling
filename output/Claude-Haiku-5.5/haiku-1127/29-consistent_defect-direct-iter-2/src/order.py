"""Order creation, assignment and the best-rider selection algorithm."""

import logging
from typing import TYPE_CHECKING, List, Optional, Tuple

import globalvar
from order_model import Order, manhattan

if TYPE_CHECKING:  # pragma: no cover
    from rider import Rider

logger = logging.getLogger(__name__)


def find_best_rider_for_order(order: Order) -> Optional["Rider"]:
    """Select the rider that should receive an order.

    Selection criteria, in priority order:
        1. Fewest current (active) orders.
        2. Closest to the restaurant by Manhattan distance.
        3. Lowest rider ID (deterministic tie-break).

    Args:
        order: The order to be assigned.

    Returns:
        The chosen :class:`rider.Rider`, or None if no riders exist.
    """
    riders = globalvar.get_value("riders", []) or []
    if not riders:
        return None
    target = order.res_pos
    return min(
        riders,
        key=lambda r: (
            len(r.active_orders()),
            manhattan(r.position, target),
            r.rider_id,
        ),
    )


class OrderManager:
    """Creates orders, keeps the order registry and assigns pending orders."""

    def create_order(self, restaurant_xy: Tuple[int, int],
                     customer_xy: Tuple[int, int]) -> Order:
        """Create a new order and register it in the global order list.

        Args:
            restaurant_xy: Restaurant input coordinate ``(x, y)``.
            customer_xy: Customer input coordinate ``(x, y)``.

        Returns:
            The newly created :class:`order_model.Order`.
        """
        order = Order(restaurant_xy, customer_xy)
        globalvar.get_value("orders").append(order)
        logger.info("Order %s created: %s -> %s",
                    order.id, order.res_pos, order.cus_pos)
        return order

    def all_orders(self) -> List[Order]:
        """Return every order ever created, in creation order."""
        return list(globalvar.get_value("orders", []) or [])

    def pending_orders(self) -> List[Order]:
        """Return orders that have not yet been assigned to a rider."""
        return [o for o in self.all_orders() if o.status == Order.CREATED]

    def get_order(self, order_id: int) -> Optional[Order]:
        """Look up an order by its ID.

        Args:
            order_id: Identifier of the order.

        Returns:
            The matching order, or None.
        """
        for order in self.all_orders():
            if order.id == order_id:
                return order
        return None

    def assign_pending_orders(self) -> List[Tuple[Order, "Rider"]]:
        """Assign every pending order to the best available rider.

        Returns:
            List of ``(order, rider)`` pairs that were assigned in this call.
        """
        assigned: List[Tuple[Order, "Rider"]] = []
        for order in self.pending_orders():
            rider = find_best_rider_for_order(order)
            if rider is None:
                break
            rider.orders.append(order)
            order.assign_to(rider.rider_id)
            assigned.append((order, rider))
            logger.info("Order %s assigned to rider %s",
                        order.id, rider.rider_id)
        return assigned
