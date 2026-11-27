"""Order assignment logic and the order manager.

Assignment strategy: the closest idle rider is preferred. When no rider is
idle, the least-loaded riders are considered, and the closest of those is
chosen, which balances the load across riders.
"""

from typing import Callable, List, Optional

import globalvar
from order_model import Order
from path_planner import euclidean
from rider import IDLE, Rider


def find_best_rider_for_order(order: Order) -> Optional[Rider]:
    """Choose the rider that should serve ``order``.

    Distance is the Euclidean distance between the rider position and the
    restaurant: ``sqrt((rider_x - restaurant_x)^2 + (rider_y - restaurant_y)^2)``.

    Args:
        order: The order to assign.

    Returns:
        The selected rider, or ``None`` if no rider exists.
    """
    riders: List[Rider] = globalvar.get_value("riders") or []
    if not riders:
        return None
    idle = [rider for rider in riders if rider.state == IDLE and not rider.orders]
    if idle:
        pool = idle
    else:
        lowest_load = min(len(rider.orders) for rider in riders)
        pool = [rider for rider in riders if len(rider.orders) == lowest_load]
    return min(
        pool,
        key=lambda rider: (euclidean(rider.position, order.res_pos), rider.rider_id),
    )


class OrderManager:
    """Creates orders and tracks pending and historical orders.

    Attributes:
        pending: Orders waiting for a rider.
        history: Every order created in this session, in creation order.
    """

    def __init__(self) -> None:
        """Create an empty order manager."""
        self.pending: List[Order] = []
        self.history: List[Order] = []

    def create_order(self, res_pos, cus_pos) -> Order:
        """Create a new order and place it in the pending queue.

        Args:
            res_pos: Restaurant ``(x, y)``.
            cus_pos: Customer ``(x, y)``.

        Returns:
            The newly created order.
        """
        order = Order(res_pos, cus_pos)
        self.pending.append(order)
        self.history.append(order)
        return order

    def assign(self, order: Order, rider: Rider) -> None:
        """Assign ``order`` to ``rider`` and remove it from the pending queue.

        Args:
            order: The order to assign.
            rider: The rider receiving the order.
        """
        order.assign_to(rider.rider_id)
        rider.orders.append(order)
        if order in self.pending:
            self.pending.remove(order)

    def dispatch_pending(self, recruit: Callable[[int], int]) -> List[Order]:
        """Assign as many pending orders as possible.

        Before each assignment the ``recruit`` callback is invoked with the
        current number of pending orders so that the system can recruit riders
        when pending orders exceed idle riders.

        Args:
            recruit: Callable taking the pending count and returning the number
                of riders added.

        Returns:
            Orders that were assigned during this call.
        """
        assigned: List[Order] = []
        for order in list(self.pending):
            recruit(len(self.pending))
            rider = find_best_rider_for_order(order)
            if rider is None:
                continue
            self.assign(order, rider)
            assigned.append(order)
        return assigned
