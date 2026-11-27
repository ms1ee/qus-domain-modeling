"""Order creation, rider assignment and completion bookkeeping."""

import logging
from typing import Any, Dict, List, Optional

import globalvar
from order_model import STATUS_ASSIGNED, STATUS_COMPLETED, STATUS_PENDING, Order
from path_planner import PathPlanner, manhattan
from rider import Rider
from system import SystemManager

logger = logging.getLogger(__name__)


class OrderError(Exception):
    """Raised when an order cannot be accepted by the system."""


def find_best_rider_for_order(order: Order) -> Rider:
    """Choose the rider that should take ``order``.

    Selection key, in priority order:
        1. Fewest active (uncompleted) orders.
        2. Smallest Manhattan distance to the restaurant.
        3. Lowest rider ID (deterministic tie-break).

    Args:
        order: The order to assign.

    Returns:
        The chosen rider, or None if there are no riders. The interface
        returns Rider; None signals that no rider is available.
    """
    riders = globalvar.get_value("riders", []) or []
    best: Optional[Rider] = None
    best_key = None
    for rider in riders:
        key = (
            len(rider.active_orders()),
            manhattan(rider.position, order.res_pos),
            rider.rider_id,
        )
        if best_key is None or key < best_key:
            best = rider
            best_key = key
    return best


class OrderManager:
    """Creates, assigns and tracks orders for the dispatch system."""

    def __init__(self, system_manager: SystemManager) -> None:
        """Create an order manager bound to a system manager.

        Args:
            system_manager: Source of funds and rider recruitment.
        """
        self._system = system_manager
        self._planner = PathPlanner()

    @property
    def orders(self) -> List[Order]:
        """All orders created in this session, in creation order."""
        return globalvar.get_value("orders", [])

    def pending_count(self) -> int:
        """Return the number of orders not yet started by a rider."""
        return sum(1 for o in self.orders
                   if o.status in (STATUS_PENDING, STATUS_ASSIGNED))

    def completed_orders(self) -> List[Order]:
        """Return all completed orders."""
        return [o for o in self.orders if o.status == STATUS_COMPLETED]

    def submit_order(self, res_pos, cus_pos) -> Dict[str, Any]:
        """Create an order, recruit a rider if needed, and assign the order.

        Recruitment happens when funds are at least the threshold and the
        number of pending orders (including this one) exceeds the number of
        idle riders.

        Args:
            res_pos: ``(x, y)`` restaurant coordinates.
            cus_pos: ``(x, y)`` customer coordinates.

        Returns:
            Dictionary with keys:
                ``order``: the created Order.
                ``rider``: the assigned Rider.
                ``new_rider``: True if a rider was recruited for this order.
                ``route``: start point followed by planned waypoints
                    (restaurant then customer).

        Raises:
            OrderError: If no rider is available and recruitment is not possible.
        """
        order = Order(res_pos, cus_pos)
        self.orders.append(order)
        new_rider = False
        try:
            pending = self.pending_count()
            if self._system.can_recruit() and pending > self._system.idle_rider_count():
                self._system.recruit_rider()
                new_rider = True
            rider = find_best_rider_for_order(order)
            if rider is None:
                raise OrderError("No rider available and funds are insufficient to recruit one.")
        except OrderError:
            self.orders.remove(order)
            raise

        rider.orders.append(order)
        order.assign_to(rider.rider_id)
        route_start = rider.position
        route = [route_start] + self._planner.plan_multi(
            route_start, [order.res_pos, order.cus_pos])
        logger.info("Order %s assigned to rider %s (new_rider=%s)",
                    order.id, rider.rider_id, new_rider)
        return {
            "order": order,
            "rider": rider,
            "new_rider": new_rider,
            "route": route,
        }
