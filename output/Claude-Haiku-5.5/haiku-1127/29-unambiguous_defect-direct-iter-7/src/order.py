"""Order assignment: rider selection and order lifecycle orchestration."""

import logging

import globalvar
import grid
from order_model import Order
from path_planner import PathPlanner
from system import SystemManager

LOAD_PENALTY = 150

logger = logging.getLogger("dispatch.order")


def rider_cost(rider, order):
    """Return the assignment cost of giving ``order`` to ``rider``.

    The cost is the distance from the rider to the restaurant plus a penalty
    for each order the rider already carries, which balances the load.

    Args:
        rider: A Rider instance.
        order: An Order instance.
    """
    distance = grid.manhattan(rider.position, order.res_pos)
    return distance + LOAD_PENALTY * len(rider.orders)


def find_best_rider_for_order(order):
    """Select the rider with the lowest assignment cost for an order.

    Ties are broken by fewer assigned orders, then by lower rider ID.

    Args:
        order: The Order to assign.

    Returns:
        The selected Rider.

    Raises:
        LookupError: If no riders exist.
    """
    riders = globalvar.get_value("riders", [])
    if not riders:
        raise LookupError("no riders are available")
    return min(
        riders,
        key=lambda r: (rider_cost(r, order), len(r.orders), r.rider_id),
    )


class OrderManager:
    """Create, assign and summarise delivery orders."""

    @staticmethod
    def create_order(res_pos, cus_pos):
        """Create an order from restaurant and customer coordinates.

        Args:
            res_pos: Pair ``(x, y)`` for the restaurant (0-800).
            cus_pos: Pair ``(x, y)`` for the customer (0-800).

        Returns:
            A new Order instance (not yet assigned).
        """
        return Order(res_pos, cus_pos)

    @staticmethod
    def estimate_eta(rider, order):
        """Estimate ticks until the order is delivered by ``rider``.

        Args:
            rider: The candidate Rider.
            order: The Order being considered.

        Returns:
            Estimated number of ticks.
        """
        queued = sum(o.distance for o in rider.orders)
        legs = grid.manhattan(rider.position, order.res_pos) + order.distance
        return PathPlanner.ticks_needed(queued + legs, rider.speed)

    @staticmethod
    def assign_order(order):
        """Assign an order to the best available rider.

        Recruits a new rider first if the system has no idle capacity and
        funds allow.

        Args:
            order: The Order to assign.

        Returns:
            Tuple ``(rider, new_rider, eta_ticks)`` where ``new_rider`` is
            True if a rider was recruited for this order.

        Raises:
            LookupError: If no rider could be found or recruited.
        """
        new_rider = SystemManager.ensure_capacity()
        rider = find_best_rider_for_order(order)
        eta = OrderManager.estimate_eta(rider, order)
        order.assign_to(rider.rider_id)
        rider.orders.append(order)
        globalvar.get_value("orders").append(order)
        logger.info("order %s assigned to rider %s", order.id, rider.rider_id)
        return rider, new_rider, eta
