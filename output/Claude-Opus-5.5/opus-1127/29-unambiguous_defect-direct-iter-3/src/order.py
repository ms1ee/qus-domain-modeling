"""Order assignment and management."""

import logging

import globalvar
import system
from order_model import Order
from path_planner import PathPlanner

logger = logging.getLogger("dispatch.order")


def find_best_rider_for_order(order):
    """Select the best rider for ``order``.

    Strategy (distance first):
    1. If idle riders exist, pick the one with the shortest street route to
       the restaurant (ties: fewer orders, lower id).
    2. Otherwise recruit a new rider if funds allow.
    3. Otherwise pick the busy rider whose total remaining route including
       this order is shortest (load balancing).
    4. With no riders at all and no funds, a rider is recruited anyway
       (funds may go negative).

    The order is NOT appended to the rider's order list here.
    """
    riders = globalvar.get_value("riders")
    if riders is None:
        system.init_system()
        riders = globalvar.get_value("riders")

    idle = [r for r in riders if r.is_available()]
    if idle:
        return min(idle, key=lambda r: (
            PathPlanner.path_length((r.x, r.y), order.res_pos),
            len(r.orders), r.rider_id))

    new_rider = system.recruit_rider()
    if new_rider is not None:
        return new_rider

    if riders:
        return min(riders, key=lambda r: (
            r.estimated_workload(order), len(r.orders), r.rider_id))

    return system.recruit_rider(force=True)


class OrderManager:
    """Handles order creation, assignment and queries."""

    def create_order(self, res_x, res_y, cus_x, cus_y):
        """Create and assign an order.

        Returns a dict with keys ``order``, ``rider``, ``new_rider`` (bool)
        and ``route`` (polyline of the rider's planned route).
        """
        riders = globalvar.get_value("riders") or []
        before = len(riders)
        order = Order((res_x, res_y), (cus_x, cus_y))
        rider = find_best_rider_for_order(order)
        order.assign_to(rider.rider_id)
        rider.orders.append(order)
        new_rider = len(globalvar.get_value("riders")) > before
        route = rider.planned_route()
        logger.info("Order %s assigned to rider %s", order.id, rider.rider_id)
        return {"order": order, "rider": rider, "new_rider": new_rider,
                "route": route}

    @staticmethod
    def all_orders():
        return list(globalvar.get_value("orders") or [])

    @staticmethod
    def completed_orders():
        return [o for o in OrderManager.all_orders()
                if o.status == "completed"]
