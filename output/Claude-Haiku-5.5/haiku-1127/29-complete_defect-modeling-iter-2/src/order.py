"""Order management: creation, rider assignment and completion tracking."""

import logging
from typing import List, Optional, Tuple

from globalvar import get_value
from order_model import STATUS_COMPLETED, Order
from path_planner import default_planner
from rider import Rider
from settings import CONFIG

logger = logging.getLogger("dispatch")


def _grid_distance(rider: Rider, node: Tuple[int, int]) -> int:
    """Return the street distance between a rider's node and a grid node."""
    col, row = default_planner().snap((rider.x, rider.y))
    return (abs(col - node[0]) + abs(row - node[1])) * CONFIG["cell_size"]


def find_best_rider_for_order(order: Order) -> Optional[Rider]:
    """Choose the rider that should take an order.

    Strategy: closest rider first, with a load penalty per queued order so
    that work is spread across riders. Riders at their queue limit are skipped.

    Args:
        order: The order to be assigned.

    Returns:
        The best Rider, or None if no rider can accept the order.
    """
    riders = get_value("riders") or []
    limit = CONFIG["max_orders_per_rider"]
    penalty = CONFIG["load_penalty"]
    best: Optional[Rider] = None
    best_score: Optional[int] = None
    for rider in riders:
        load = len(rider.orders)
        if load >= limit:
            continue
        score = _grid_distance(rider, order.res_node) + penalty * load
        if best_score is None or score < best_score:
            best = rider
            best_score = score
    return best


class OrderManager:
    """Creates orders, assigns them to riders and tracks their completion.

    Attributes:
        orders: Every order ever created, in creation order.
        pending: Orders waiting for a rider.
        active: Assigned orders that are not yet completed.
        completed: Delivered orders.
    """

    def __init__(self) -> None:
        self.orders: List[Order] = []
        self.pending: List[Order] = []
        self.active: List[Order] = []
        self.completed: List[Order] = []

    def create_order(self, res_xy, cus_xy, start_time: int) -> Order:
        """Create an order and place it in the pending queue.

        Raises:
            ValueError: If either position is invalid.
        """
        order = Order(res_xy, cus_xy, start_time=start_time)
        self.orders.append(order)
        self.pending.append(order)
        logger.info("Order %s created (restaurant=%s customer=%s)",
                    order.id, order.res_pos, order.cus_pos)
        return order

    def try_assign(self, order: Order) -> Optional[Rider]:
        """Attempt to assign a pending order to the best rider.

        Returns:
            The rider that received the order, or None if none is available.
        """
        rider = find_best_rider_for_order(order)
        if rider is None:
            return None
        route = default_planner().plan_route(
            (rider.x, rider.y),
            [order.res_pos.center, order.cus_pos.center],
            rider.speed,
        )
        order.distance = route.total_distance
        order.assign_to(rider.rider_id)
        rider.orders.append(order)
        if order in self.pending:
            self.pending.remove(order)
        self.active.append(order)
        logger.info("Order %s assigned to rider %s", order.id, rider.rider_id)
        return rider

    def assign_pending(self) -> List[Tuple[Order, Rider]]:
        """Try to assign every pending order.

        Returns:
            List of (order, rider) pairs that were assigned in this call.
        """
        assigned: List[Tuple[Order, Rider]] = []
        for order in list(self.pending):
            rider = self.try_assign(order)
            if rider is not None:
                assigned.append((order, rider))
        return assigned

    def collect_completed(self) -> List[Order]:
        """Move delivered orders from the active list to the completed list.

        Returns:
            Orders that were completed since the last call.
        """
        done = [order for order in self.active if order.status == STATUS_COMPLETED]
        if done:
            self.active = [o for o in self.active if o.status != STATUS_COMPLETED]
            self.completed.extend(done)
        return done
