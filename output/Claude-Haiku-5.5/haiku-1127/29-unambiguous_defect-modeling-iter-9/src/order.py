"""Order creation, distance-first rider assignment and load balancing."""

import logging
from typing import List

import globalvar
import system
from config import get_config
from order_model import Order
from pathplanner import PathPlanner
from rider import IDLE, Rider

logger = logging.getLogger(__name__)


class NoRiderAvailableError(RuntimeError):
    """Raised when no rider can take the order and none can be recruited."""


def create_order(res_pos, cus_pos) -> Order:
    """Create an order and register it in the global order list.

    Args:
        res_pos: Restaurant ``(x, y)`` in 0..800.
        cus_pos: Customer ``(x, y)`` in 0..800.

    Returns:
        The newly created ``Order``.
    """
    order = Order(res_pos, cus_pos)
    orders: List[Order] = globalvar.get_value("orders", [])
    orders.append(order)
    globalvar.set_value("orders", orders)
    logger.info("Order %d created: restaurant %s, customer %s",
                order.id, order.res_pos, order.cus_pos)
    return order


def cancel_order(order: Order) -> None:
    """Cancel an order and remove it from the global order list.

    Args:
        order: The order to cancel.
    """
    order.cancel()
    orders: List[Order] = globalvar.get_value("orders", [])
    if order in orders:
        orders.remove(order)


def _score(rider: Rider, order: Order) -> int:
    """Return the assignment cost of ``rider`` for ``order`` (lower is better).

    The cost is the Manhattan distance from the rider to the restaurant plus a
    penalty for each order the rider already carries, which balances load.
    """
    cfg = get_config()
    distance = abs(rider.x - order.restaurant_x) + abs(rider.y - order.restaurant_y)
    return distance + cfg.load_penalty * len(rider.orders)


def find_best_rider_for_order(order: Order) -> Rider:
    """Select the most suitable rider for an order.

    Strategy:
        1. Consider riders that still have capacity for another order.
        2. If no rider is idle and a recruit is affordable, recruit one.
        3. Otherwise pick the rider with the lowest distance-plus-load score.

    Args:
        order: The order needing a rider.

    Returns:
        The chosen ``Rider`` (possibly newly recruited).

    Raises:
        NoRiderAvailableError: If no rider has capacity and none can be recruited.
    """
    cfg = get_config()
    riders: List[Rider] = system.get_riders()
    candidates = [r for r in riders if len(r.orders) < cfg.max_orders_per_rider]
    idle = [r for r in candidates if r.state == IDLE and not r.orders]

    if not idle and system.can_recruit():
        return system.recruit_rider()
    if not candidates:
        raise NoRiderAvailableError("all riders are fully loaded and funds are insufficient")
    return min(candidates, key=lambda r: (_score(r, order), r.rider_id))


def assign_order(order: Order) -> Rider:
    """Assign an order to the best rider and update both sides of the link.

    The order's distance is set to the street-route length from restaurant to
    customer. The rider receives the order by appending it to ``rider.orders``.

    Args:
        order: The order to assign.

    Returns:
        The rider that received the order.

    Raises:
        NoRiderAvailableError: If assignment is impossible.
    """
    rider = find_best_rider_for_order(order)
    route = [order.res_pos] + PathPlanner.plan(order.res_pos, order.cus_pos)
    order.distance = float(PathPlanner.route_length(route))
    rider.orders.append(order)
    order.assign_to(rider.rider_id)
    logger.info("Order %d assigned to rider %d", order.id, rider.rider_id)
    return rider
