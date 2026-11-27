"""Order dispatch: rider selection and assignment."""

import logging
import math

import globalvar
from order_model import PENDING, Order
from system import SystemManager

logger = logging.getLogger(__name__)


def _now():
    """Return the current simulated tick (0 if unset)."""
    return globalvar.get_value("tick") or 0


def find_best_rider_for_order(order):
    """Choose the best rider for an order.

    Strategy: the closest rider (Euclidean distance from the rider to the
    restaurant, as in the PRD formula) wins. Ties are broken by the fewest
    current active orders, then by rider id.

    Args:
        order: The order needing a rider.

    Returns:
        Rider or None: The chosen rider, or None if no riders exist.
    """
    riders = globalvar.get_value("riders") or []
    if not riders:
        return None
    rest_x, rest_y = order.res_pos

    def rank(rider):
        distance = math.hypot(rider.x - rest_x, rider.y - rest_y)
        load = len(rider.active_orders())
        return (distance, load, rider.rider_id)

    return min(riders, key=rank)


class OrderManager:
    """Creates, dispatches and lists orders."""

    @staticmethod
    def create_order(res_pos, cus_pos):
        """Validate coordinates, create an order and store it.

        Args:
            res_pos: Restaurant ``(x, y)``.
            cus_pos: Customer ``(x, y)``.

        Returns:
            Order: The stored pending order.

        Raises:
            ValueError: If coordinates are invalid.
        """
        order = Order(res_pos, cus_pos, created_tick=_now())
        globalvar.get_value("orders").append(order)
        return order

    @staticmethod
    def all_orders():
        """Return a copy of all orders created so far."""
        return list(globalvar.get_value("orders") or [])

    @staticmethod
    def pending_orders():
        """Return orders that have not yet been assigned."""
        return [o for o in OrderManager.all_orders() if o.status == PENDING]

    @staticmethod
    def dispatch(order):
        """Recruit if needed, pick the best rider and assign the order.

        Args:
            order: A pending order.

        Returns:
            dict: ``{"rider": Rider or None, "new_rider": bool}``.

        Raises:
            ValueError: If the order is not pending.
        """
        if order.status != PENDING:
            raise ValueError(f"Order #{order.id} is not pending")
        pending = len(OrderManager.pending_orders())
        recruited = SystemManager.maybe_recruit(pending)
        rider = find_best_rider_for_order(order)
        if rider is None:
            logger.warning("No rider available for order #%d", order.id)
            return {"rider": None, "new_rider": False}
        order.assign_to(rider.rider_id)
        rider.orders.append(order)
        return {"rider": rider, "new_rider": recruited is not None}
