"""Order creation, assignment, and dispatch logic."""

import logging

import globalvar
from order_model import Order
from path_planner import euclidean

logger = logging.getLogger("dispatch.dispatch")


def _find_rider(rider_id):
    """Return the rider with ``rider_id`` from the global roster, or None."""
    for rider in globalvar.get_value("riders") or []:
        if rider.rider_id == rider_id:
            return rider
    return None


def find_best_rider_for_order(order):
    """Choose the rider that should receive ``order``.

    The rider with the fewest unfinished orders is preferred. Ties are broken
    by the Euclidean distance from the rider to the restaurant, so the
    closest rider wins among equally loaded riders.

    Args:
        order: The order that needs a rider.

    Returns:
        The selected Rider, or None if the roster is empty.
    """
    riders = globalvar.get_value("riders") or []
    if not riders:
        return None

    def sort_key(rider):
        return (
            rider.active_order_count(),
            euclidean((rider.x, rider.y), order.restaurant),
            rider.rider_id,
        )

    return min(riders, key=sort_key)


class OrderManager:
    """Creates orders, keeps the pending queue, and dispatches riders."""

    def __init__(self, system):
        """Create a manager bound to a SystemManager.

        Args:
            system: SystemManager used for rider recruitment.
        """
        self.system = system

    def create_order(self, res_pos, cus_pos):
        """Create an order and add it to the history and pending queue.

        Args:
            res_pos: ``(x, y)`` restaurant coordinates.
            cus_pos: ``(x, y)`` customer coordinates.

        Returns:
            The newly created Order.
        """
        order = Order(res_pos, cus_pos)
        globalvar.get_value("orders").append(order)
        globalvar.get_value("pending_orders").append(order)
        logger.info("Order #%s created: %s -> %s", order.id, order.restaurant, order.customer)
        return order

    def dispatch_pending(self):
        """Assign pending orders to riders, recruiting when needed.

        For each pending order a rider is recruited if pending orders exceed
        idle riders and funds allow it. The order is then assigned to the best
        rider. Processing stops when no rider is available.

        Returns:
            Tuple ``(assigned_orders, new_rider_ids)``.
        """
        pending = globalvar.get_value("pending_orders")
        assigned = []
        new_rider_ids = []
        for order in list(pending):
            recruited = self.system.maybe_recruit(len(pending))
            if recruited is not None:
                new_rider_ids.append(recruited.rider_id)
            rider = find_best_rider_for_order(order)
            if rider is None:
                break
            pending.remove(order)
            order.assign_to(rider.rider_id)
            assigned.append(order)
        return assigned, new_rider_ids

    def place_order(self, res_pos, cus_pos):
        """Create an order and try to dispatch it immediately.

        Args:
            res_pos: ``(x, y)`` restaurant coordinates.
            cus_pos: ``(x, y)`` customer coordinates.

        Returns:
            Dict with keys "order" (Order), "rider" (Rider or None when the
            order is still pending) and "new_riders" (list of new rider ids).
        """
        order = self.create_order(res_pos, cus_pos)
        _, new_rider_ids = self.dispatch_pending()
        rider = _find_rider(order.rider_id) if order.rider_id is not None else None
        return {"order": order, "rider": rider, "new_riders": new_rider_ids}
