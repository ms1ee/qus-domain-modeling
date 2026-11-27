"""Order management: creation, rider selection, recruitment and assignment."""

import logging
import math
from typing import Any, Dict, List

import globalvar
from config import param
from order_model import Order
from path_planner import PathPlanner
from rider import occupancy_map
from system import get_system

logger = logging.getLogger("dispatch.order")


def _order_registry() -> List[Order]:
    """Return the global order list, creating it if necessary."""
    registry = globalvar.get_value("orders")
    if registry is None:
        registry = []
        globalvar.set_value("orders", registry)
    return registry


def find_best_rider_for_order(order: Order):
    """Select the most suitable rider for ``order``.

    The score combines the street distance from the rider to the restaurant
    with a load penalty for each order the rider already holds. This favours
    nearby riders (distance-first) while balancing the load across riders.
    Ties are resolved by the lower rider ID. If no riders exist, one is
    recruited when funds allow.

    Args:
        order: The order to be assigned.

    Returns:
        The chosen ``Rider``.

    Raises:
        RuntimeError: If no rider exists and none can be recruited.
    """
    riders = globalvar.get_value("riders", []) or []
    if not riders:
        recruited = get_system().recruit_rider()
        if recruited is None:
            raise RuntimeError("no rider available and recruitment is not possible")
        riders = globalvar.get_value("riders", [])

    planner = PathPlanner()
    best = None
    best_score = None
    for rider in riders:
        to_restaurant = planner.plan(rider.position, order.res_pos,
                                     occupancy_map(exclude=rider))
        pickup_distance = planner.route_length(rider.position, to_restaurant)
        score = pickup_distance + param("load_penalty") * len(rider.orders)
        if (best is None or score < best_score
                or (score == best_score and rider.rider_id < best.rider_id)):
            best, best_score = rider, score
    logger.info("Order %s best rider %s (score %s)", order.id, best.rider_id, best_score)
    return best


class OrderManager:
    """Create, assign and track orders."""

    def __init__(self) -> None:
        self.planner = PathPlanner()

    def create_order(self, res_pos, cus_pos) -> Order:
        """Create an order and register it in the order history.

        Args:
            res_pos: Restaurant ``(x, y)`` in 0-800.
            cus_pos: Customer ``(x, y)`` in 0-800.

        Returns:
            The new ``Order``.
        """
        order = Order(res_pos, cus_pos, created_tick=globalvar.get_value("tick", 0))
        _order_registry().append(order)
        logger.info("Created order %s: restaurant %s customer %s",
                    order.id, order.res_pos, order.cus_pos)
        return order

    def all_orders(self) -> List[Order]:
        """Return every order created during this session."""
        return list(_order_registry())

    def active_orders(self) -> List[Order]:
        """Return orders that are neither completed nor rejected."""
        return [o for o in _order_registry() if o.status not in ("completed", "rejected")]

    def _ensure_capacity(self) -> bool:
        """Recruit a rider when no rider is free and funds allow.

        Returns:
            True if a new rider was added.
        """
        riders = globalvar.get_value("riders", []) or []
        if any(not rider.orders for rider in riders):
            return False
        return get_system().recruit_rider() is not None

    def assign_order(self, order: Order) -> Dict[str, Any]:
        """Assign ``order`` to the best rider and compute the planned route.

        Args:
            order: An order created by ``create_order``.

        Returns:
            Dictionary with keys ``rider``, ``new_rider`` (bool), ``restaurant``,
            ``customer``, ``route`` (list of points starting at the rider's
            position), ``distance`` and ``eta_ticks``.

        Raises:
            RuntimeError: If no rider can serve the order.
        """
        added = self._ensure_capacity()
        try:
            rider = find_best_rider_for_order(order)
        except RuntimeError:
            order.status = "rejected"
            raise

        occupancy = occupancy_map(exclude=rider)
        start = rider.position
        to_restaurant = self.planner.plan(start, order.res_pos, occupancy)
        to_customer = self.planner.plan(order.res_pos, order.cus_pos, occupancy)
        distance = (self.planner.route_length(start, to_restaurant)
                    + self.planner.route_length(order.res_pos, to_customer))
        backlog = rider.remaining_distance()
        eta_ticks = math.ceil((backlog + distance) / rider.speed) if rider.speed else 0

        order.assign_to(rider.rider_id)
        rider.orders.append(order)
        logger.info("Order %s assigned to rider %s (new rider: %s)",
                    order.id, rider.rider_id, added)
        return {
            "rider": rider,
            "new_rider": added,
            "restaurant": order.res_pos,
            "customer": order.cus_pos,
            "route": [start] + to_restaurant + to_customer,
            "distance": distance,
            "eta_ticks": eta_ticks,
        }
