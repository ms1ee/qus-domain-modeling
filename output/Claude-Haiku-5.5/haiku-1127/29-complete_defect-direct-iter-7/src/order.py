"""Order management: creation, distance-first rider assignment and queueing."""

from __future__ import annotations

import logging
import math
from typing import TYPE_CHECKING, Optional

import config
import globalvar
from order_model import (
    COMPLETED_STATUS_SENTINEL,
    STATUS_COMPLETED,
    STATUS_CREATED,
    Order,
    manhattan,
)
from path_planner import PathPlanner

if TYPE_CHECKING:  # pragma: no cover - imported for type hints only
    from rider import Rider

logger = logging.getLogger("dispatch.order")


def find_best_rider_for_order(order: Order) -> Optional["Rider"]:
    """Select the rider that should receive an order.

    Strategy: closest rider first.  Each rider is scored by its Manhattan
    distance to the restaurant plus a load penalty per already-assigned
    order, which spreads work across riders.  Riders already holding
    MAX_ORDERS_PER_RIDER orders are not candidates.  Ties go to the lower
    rider id.

    Args:
        order: The order needing a rider.

    Returns:
        Rider or None: The chosen rider, or None if no rider can accept it.
    """
    best = None
    best_score = None
    for rider in globalvar.get_value("riders", []) or []:
        if len(rider.orders) >= config.MAX_ORDERS_PER_RIDER:
            continue
        distance = manhattan(rider.position, order.res_pos)
        score = distance + len(rider.orders) * config.LOAD_PENALTY
        if (best is None or score < best_score
                or (score == best_score and rider.rider_id < best.rider_id)):
            best = rider
            best_score = score
    return best


class OrderManager:
    """Creates orders, assigns them to riders and keeps the order queue.

    All state lives in the global store: "orders" (history) and
    "pending_orders" (waiting for a rider).
    """

    @staticmethod
    def all_orders() -> list:
        """Return the list of all tracked orders."""
        return globalvar.get_value("orders", []) or []

    @staticmethod
    def pending_orders() -> list:
        """Return the list of orders waiting for a rider."""
        return globalvar.get_value("pending_orders", []) or []

    def create_order(self, restaurant, customer) -> Order:
        """Create and register a new order from raw coordinates.

        Args:
            restaurant: Restaurant (x, y) in 0-800.
            customer: Customer (x, y) in 0-800.

        Returns:
            Order: The newly created order (status "created").

        Raises:
            ValueError: If the coordinates are invalid.
        """
        tick = int(globalvar.get_value("tick", 0))
        order = Order(restaurant, customer, start_tick=tick)
        self.all_orders().append(order)
        self._trim_history()
        logger.info("Created order %d at tick %d", order.id, tick)
        return order

    def assign_order(self, order: Order) -> Optional["Rider"]:
        """Assign an order to the best rider, or queue it if none is free.

        Args:
            order: Order in status "created".

        Returns:
            Rider or None: The rider the order was assigned to, or None if
            the order was placed in the pending queue.
        """
        rider = find_best_rider_for_order(order)
        if rider is None:
            if order not in self.pending_orders():
                self.pending_orders().append(order)
            logger.info("No rider available; order %d queued", order.id)
            return None
        if order in self.pending_orders():
            self.pending_orders().remove(order)
        self._attach(order, rider)
        return rider

    def assign_pending(self) -> list[tuple[Order, "Rider"]]:
        """Try to assign every queued order to a rider.

        Returns:
            list: (order, rider) pairs that were assigned in this call.
        """
        assigned = []
        for order in list(self.pending_orders()):
            rider = find_best_rider_for_order(order)
            if rider is None:
                continue
            self.pending_orders().remove(order)
            self._attach(order, rider)
            assigned.append((order, rider))
        return assigned

    @staticmethod
    def _attach(order: Order, rider: "Rider") -> None:
        """Link an order to a rider and compute its route estimates.

        Args:
            order: The order to attach.
            rider: The rider receiving the order.
        """
        route = PathPlanner.plan_route(rider.position,
                                       [order.res_pos, order.cus_pos])
        length = PathPlanner.route_length(rider.position, route)
        order.pickup_distance = manhattan(rider.position, order.res_pos)
        order.estimated_ticks = math.ceil(length / rider.speed)
        order.assign_to(rider.rider_id)
        rider.orders.append(order)

    def _trim_history(self) -> None:
        """Drop the oldest completed orders when the history is too long."""
        orders = self.all_orders()
        while len(orders) > config.HISTORY_LIMIT:
            index = next(
                (i for i, o in enumerate(orders)
                 if o.status == STATUS_COMPLETED),
                None,
            )
            if index is None:
                break
            del orders[index]
