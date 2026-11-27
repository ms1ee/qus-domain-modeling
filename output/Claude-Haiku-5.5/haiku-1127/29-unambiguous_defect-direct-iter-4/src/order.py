"""Order creation, rider assignment and pending-order management."""

import logging

import globalvar
from order_model import Order
from path_planner import manhattan

logger = logging.getLogger(__name__)

LOAD_PENALTY = 300


def find_best_rider_for_order(order):
    """Select the best rider for an order.

    The score is the Manhattan distance from the rider to the restaurant plus
    a load penalty per already assigned order, so nearby, lightly loaded riders
    win (distance-first with load balancing). Ties go to the lower list index.

    Args:
        order: The :class:`order_model.Order` to assign.

    Returns:
        The selected :class:`rider.Rider`, or None if no riders exist.
    """
    riders = globalvar.get_value("riders") or []
    best = None
    best_score = None
    for rider in riders:
        score = manhattan(rider.position, order.res_pos) + LOAD_PENALTY * len(rider.orders)
        if best is None or score < best_score:
            best = rider
            best_score = score
    return best


class OrderManager:
    """Creates orders, dispatches them to riders and tracks their lifecycle."""

    def __init__(self):
        """Ensure the global order registries exist."""
        if globalvar.get_value("orders") is None:
            globalvar.set_value("orders", [])
        if globalvar.get_value("pending_orders") is None:
            globalvar.set_value("pending_orders", [])

    def create_order(self, res_x, res_y, cus_x, cus_y):
        """Validate coordinates, create an order and register it.

        Args:
            res_x: Restaurant x (0-800).
            res_y: Restaurant y (0-800).
            cus_x: Customer x (0-800).
            cus_y: Customer y (0-800).

        Returns:
            The created :class:`order_model.Order`.

        Raises:
            ValueError: If any coordinate is outside 0-800.
        """
        for name, value in (("restaurant x", res_x), ("restaurant y", res_y),
                            ("customer x", cus_x), ("customer y", cus_y)):
            if not 0 <= int(value) <= 800:
                raise ValueError(f"{name} must be between 0 and 800, got {value}")
        order = Order((res_x, res_y), (cus_x, cus_y))
        globalvar.get_value("orders").append(order)
        logger.info("Order %s created", order.id)
        return order

    def _recruit_if_needed(self):
        """Recruit a rider when none is available and funds allow.

        Returns:
            True if a new rider was recruited.
        """
        riders = globalvar.get_value("riders") or []
        if any(rider.is_available() for rider in riders):
            return False
        system = globalvar.get_value("system")
        if system is None:
            return False
        return system.recruit_rider() is not None

    def dispatch(self, order):
        """Assign an order to the best available rider.

        Args:
            order: Order to dispatch.

        Returns:
            Tuple ``(rider, new_rider_added)``. ``rider`` is None when the order
            stays pending because no rider could be assigned.
        """
        new_rider = self._recruit_if_needed()
        rider = find_best_rider_for_order(order)
        pending = globalvar.get_value("pending_orders")
        if rider is None:
            order.status = "pending"
            if order not in pending:
                pending.append(order)
            logger.warning("Order %s is pending: no rider available", order.id)
            return None, new_rider
        rider.orders.append(order)
        order.assign_to(rider.rider_id)
        if order in pending:
            pending.remove(order)
        logger.info("Order %s assigned to rider %s", order.id, rider.rider_id)
        return rider, new_rider

    def retry_pending(self):
        """Try to dispatch all pending orders again.

        Returns:
            List of orders that were successfully assigned in this call.
        """
        assigned = []
        for order in list(globalvar.get_value("pending_orders") or []):
            rider, _ = self.dispatch(order)
            if rider is not None:
                assigned.append(order)
        return assigned

    @staticmethod
    def all_orders():
        """Return all orders created in this session."""
        return list(globalvar.get_value("orders") or [])

    @staticmethod
    def pending_orders():
        """Return orders waiting for a rider."""
        return list(globalvar.get_value("pending_orders") or [])

    def completed_orders(self):
        """Return all completed orders."""
        return [order for order in self.all_orders() if order.status == "completed"]
