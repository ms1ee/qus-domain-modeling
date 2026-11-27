"""Order management: creation, assignment, recruitment and completion."""

import logging

import globalvar
from order_model import Order
from rider import Rider  # noqa: F401  (used for type reference)

LOGGER = logging.getLogger("dispatch.order")


def find_best_rider_for_order(order):
    """Choose the rider that should serve ``order``.

    Strategy: only riders with the fewest active orders are considered (the
    order always goes to the least-loaded rider), and among those the rider
    with the smallest Manhattan distance to the restaurant wins.

    Args:
        order: The Order to be assigned.

    Returns:
        The selected Rider, or None if no rider exists.
    """
    riders = globalvar.get_value("riders") or []
    if not riders:
        return None
    min_load = min(rider.active_order_count() for rider in riders)
    candidates = [r for r in riders if r.active_order_count() == min_load]
    return min(
        candidates,
        key=lambda r: (abs(r.x - order.restaurant_x) + abs(r.y - order.restaurant_y),
                       r.rider_id),
    )


class OrderManager:
    """Creates, assigns and tracks orders for the dispatch system."""

    def __init__(self, system):
        """Create an order manager bound to a SystemManager.

        Args:
            system: The SystemManager that owns funds and riders.
        """
        self.system = system
        self.orders = []

    def create_order(self, restaurant_pos, customer_pos):
        """Create and register a new pending order.

        Args:
            restaurant_pos: (x, y) restaurant location.
            customer_pos: (x, y) customer location.

        Returns:
            The created Order.
        """
        order = Order(restaurant_pos, customer_pos)
        self.orders.append(order)
        return order

    def pending_orders(self):
        """Return orders that have not yet been assigned to a rider."""
        return [o for o in self.orders if o.status == "pending"]

    def completed_orders(self):
        """Return the list of delivered orders."""
        return [o for o in self.orders if o.status == "completed"]

    def _recruit_if_needed(self):
        """Recruit riders while pending orders exceed idle riders.

        Returns:
            True if at least one rider was recruited.
        """
        added = False
        while len(self.pending_orders()) > len(self.system.idle_riders()):
            if self.system.recruit_rider() is None:
                break
            added = True
        return added

    def assign(self, order):
        """Assign ``order`` to the best rider and append it to that rider.

        Args:
            order: The pending Order.

        Returns:
            The Rider that received the order, or None if none is available.
        """
        rider = find_best_rider_for_order(order)
        if rider is None:
            return None
        order.assign_to(rider.rider_id)
        rider.orders.append(order)
        LOGGER.info("Order %s assigned to rider %s", order.id, rider.rider_id)
        return rider

    def submit_order(self, restaurant_pos, customer_pos):
        """Create an order, recruit if needed, and assign it.

        Args:
            restaurant_pos: (x, y) restaurant location.
            customer_pos: (x, y) customer location.

        Returns:
            Tuple (order, rider_or_none, new_rider_added).
        """
        order = self.create_order(restaurant_pos, customer_pos)
        added = self._recruit_if_needed()
        rider = self.assign(order)
        return order, rider, added

    def assign_pending(self):
        """Try to assign every pending order; return how many were assigned."""
        assigned = 0
        for order in self.pending_orders():
            self._recruit_if_needed()
            if self.assign(order) is not None:
                assigned += 1
        return assigned
