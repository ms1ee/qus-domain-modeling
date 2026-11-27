"""Order assignment and order management.

Provides :func:`find_best_rider_for_order` (closest-rider assignment with a
load-balancing penalty), :func:`assign_order`, and :class:`OrderManager`,
which validates input, dispatches orders, recruits riders and tracks
pending orders.
"""

import logging
import math

import globalvar
from constants import LOAD_PENALTY, ORDER_COMPLETED
from order_model import Order

logger = logging.getLogger(__name__)


def find_best_rider_for_order(order):
    """Select the best rider for an order.

    The score of each rider is the Euclidean distance from the rider to the
    restaurant plus LOAD_PENALTY for every order already queued on that rider.
    The lowest score wins; ties go to the lower rider_id. This favours the
    closest rider while balancing load among competing riders.

    Args:
        order: The Order to assign.

    Returns:
        Rider | None: The chosen rider, or None if no riders exist.
    """
    riders = globalvar.get_value("riders", []) or []
    best = None
    best_score = None
    for rider in riders:
        distance = math.hypot(rider.x - order.res_pos[0], rider.y - order.res_pos[1])
        score = distance + LOAD_PENALTY * len(rider.orders)
        if (best is None or score < best_score
                or (score == best_score and rider.rider_id < best.rider_id)):
            best = rider
            best_score = score
    return best


def assign_order(order, rider):
    """Assign ``order`` to ``rider`` by appending it to the rider's order list.

    Args:
        order: Order to assign.
        rider: Rider receiving the order.
    """
    rider.orders.append(order)
    order.assign_to(rider.rider_id)
    logger.info("Order %s assigned to rider %s", order.id, rider.rider_id)


class OrderManager:
    """Creates, dispatches and tracks orders.

    Args:
        system_manager: The SystemManager used for rider recruitment.
    """

    def __init__(self, system_manager):
        self.system = system_manager

    @staticmethod
    def pending_list():
        """Return the live list of pending (unassigned) orders."""
        return globalvar.get_value("pending_orders", [])

    @staticmethod
    def order_history():
        """Return the live list of all orders ever created."""
        return globalvar.get_value("orders", [])

    def create_order(self, coords):
        """Create and register an order from four integer coordinates.

        Args:
            coords: Sequence [restaurant_x, restaurant_y, customer_x, customer_y].

        Returns:
            Order: The new order.

        Raises:
            ValueError: If the coordinates are invalid.
        """
        values = list(coords)
        if len(values) != 4:
            raise ValueError("an order needs exactly four coordinates")
        order = Order(values[0:2], values[2:4])
        self.order_history().append(order)
        logger.info("Order %s created", order.id)
        return order

    def _try_assign(self, order):
        """Attempt to recruit if needed, pick a rider and assign the order.

        Returns:
            dict | None: Result information, or None if no rider is available.
        """
        recruited = self.system.try_recruit(len(self.pending_list()))
        rider = find_best_rider_for_order(order)
        if rider is None:
            return None
        if order in self.pending_list():
            self.pending_list().remove(order)
        assign_order(order, rider)
        return {
            "order": order,
            "rider": rider,
            "recruited": recruited,
        }

    def dispatch(self, order):
        """Queue a new order and try to assign it immediately.

        Args:
            order: The Order to dispatch.

        Returns:
            dict: Keys "order", "rider" (None if not assigned), "recruited"
            (Rider or None) and "restaurant"/"customer" centre points.
        """
        self.pending_list().append(order)
        result = self._try_assign(order)
        if result is None:
            result = {"order": order, "rider": None, "recruited": None}
        result["restaurant"] = order.res_pos
        result["customer"] = order.cus_pos
        return result

    def process_pending(self):
        """Retry assignment for every pending order.

        Returns:
            list[dict]: Results for orders that were assigned in this call.
        """
        assigned = []
        for order in list(self.pending_list()):
            result = self._try_assign(order)
            if result is not None:
                assigned.append(result)
        return assigned

    def active_orders(self):
        """Return orders that are not yet completed."""
        return [o for o in self.order_history() if o.status != ORDER_COMPLETED]
