"""Order assignment: best-rider selection and order lifecycle management."""

import logging
import math
from typing import Optional, Tuple

from globalvar import PARAMS, get_value
from order_model import Order
from path_planner import PathPlanner
from rider import Rider
from system import SystemManager

logger = logging.getLogger(__name__)

_PLANNER = PathPlanner()


def find_best_rider_for_order(order: Order) -> Rider:
    """Select the most suitable rider for ``order``.

    The score is the street distance from the rider to the restaurant plus a
    load penalty per already queued order.  Distance is the primary factor;
    the penalty balances load.  Ties are broken by rider ID.  Only riders with
    spare queue capacity are considered.

    Args:
        order: The order to be assigned.

    Returns:
        The chosen rider (not yet modified).

    Raises:
        LookupError: If there are no riders or all riders are at capacity.
    """
    riders = get_value("riders", []) or []
    if not riders:
        raise LookupError("no riders are available")
    limit = PARAMS["max_orders_per_rider"]
    candidates = [rider for rider in riders if len(rider.orders) < limit]
    if not candidates:
        raise LookupError("all riders are at full capacity")

    def score(rider: Rider) -> Tuple[int, int]:
        distance = _PLANNER.distance(rider.position(), order.res_pos)
        return (distance + PARAMS["load_penalty"] * len(rider.orders), rider.rider_id)

    return min(candidates, key=score)


class OrderManager:
    """Creates, assigns and reports on orders.

    Attributes:
        system: The SystemManager used for rider recruitment.
    """

    def __init__(self, system: SystemManager) -> None:
        """Bind the manager to a system manager.

        Args:
            system: Shared SystemManager instance.
        """
        self.system = system

    def dispatch(self, order: Order) -> Tuple[Rider, Optional[Rider]]:
        """Assign ``order`` to the best available rider.

        Recruits a new rider first when no idle rider exists and funds allow.

        Args:
            order: A pending order.

        Returns:
            Pair ``(assigned_rider, new_rider)``.  ``new_rider`` is None when no
            recruitment happened.

        Raises:
            ValueError: If the order has already been assigned.
            LookupError: If no rider can take the order.
        """
        if order.rider_id is not None or order.status != "pending":
            raise ValueError(f"order {order.id} is already assigned")
        new_rider = self.system.ensure_idle_rider()
        try:
            rider = find_best_rider_for_order(order)
        except LookupError as exc:
            raise LookupError(
                f"{exc} (funds {self.system.funds}, recruit cost {PARAMS['recruit_cost']})"
            ) from exc
        order.distance = PathPlanner.route_length(
            _PLANNER.plan(order.res_pos, order.cus_pos), order.res_pos
        )
        order.assign_to(rider.rider_id)
        rider.orders.append(order)
        get_value("orders").append(order)
        logger.info("Order %d assigned to rider %d", order.id, rider.rider_id)
        return rider, new_rider

    @staticmethod
    def full_route(rider: Rider, order: Order) -> list:
        """Return the waypoints from the rider's position through the order.

        The route covers the leg to the restaurant and then the leg to the
        customer.  The rider's current position is not included.

        Args:
            rider: The assigned rider.
            order: The order being planned.
        """
        to_restaurant = _PLANNER.plan(rider.position(), order.res_pos)
        to_customer = _PLANNER.plan(order.res_pos, order.cus_pos)
        return to_restaurant + to_customer

    @staticmethod
    def eta_ticks(rider: Rider, route: list) -> int:
        """Estimate the number of ticks needed to travel ``route``.

        Args:
            rider: Rider performing the trip (for speed and start position).
            route: Waypoints returned by ``full_route``.
        """
        length = PathPlanner.route_length(route, rider.position())
        if rider.speed <= 0:
            return 0
        return math.ceil(length / rider.speed)
