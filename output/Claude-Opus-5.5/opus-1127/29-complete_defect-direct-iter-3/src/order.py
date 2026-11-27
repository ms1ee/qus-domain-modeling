"""Order creation, assignment and completion management."""

import math

import globalvar
import system
from order_model import Order
from path_planner import PathPlanner


def find_best_rider_for_order(order):
    """Return the rider that can reach the restaurant soonest.

    The cost of a rider is the distance of all its queued work plus the
    distance from where that work ends to the order's restaurant, so idle
    nearby riders win and busy riders are naturally load-balanced. If there
    are no riders at all, one is recruited (funds may go negative).
    """
    riders = globalvar.get_value("riders")
    if riders is None:
        system.init_system()
        riders = globalvar.get_value("riders")
    if not riders:
        system.recruit_rider(charge=True)
        riders = globalvar.get_value("riders")
    best = None
    best_key = None
    for rider in riders:
        cost = rider.estimate_cost(order.res_pos)
        key = (cost, len(rider.orders), rider.rider_id)
        if best_key is None or key < best_key:
            best, best_key = rider, key
    return best


class OrderManager:
    """Handles order creation, assignment and completion queries."""

    def create_order(self, values):
        """Create and assign an order from ``[rx, ry, cx, cy]``.

        Returns a dict with the order, rider, whether a new rider was added,
        the planned route, distance and estimated ticks.
        """
        if len(values) != 4:
            raise ValueError("exactly four coordinates are required")
        riders = globalvar.get_value("riders")
        if riders is None:
            system.init_system()
            riders = globalvar.get_value("riders")
        order = Order((values[0], values[1]), (values[2], values[3]))
        before = len(riders)
        system.auto_recruit()
        rider = find_best_rider_for_order(order)
        new_rider = len(globalvar.get_value("riders")) > before
        order.assign_to(rider.rider_id)
        rider.orders.append(order)
        globalvar.get_value("orders").append(order)
        route = rider.full_route()
        distance = PathPlanner.route_length(route[0], route[1:])
        pending_accepts = sum(
            1 for o in rider.orders if o is not rider.current_order)
        est = math.ceil(distance / rider.speed) + pending_accepts
        return {
            "order": order,
            "rider": rider,
            "new_rider": new_rider,
            "route": route,
            "distance": distance,
            "estimated_ticks": est,
        }

    @staticmethod
    def all_orders():
        return list(globalvar.get_value("orders", []))

    @staticmethod
    def completed_orders():
        return [o for o in globalvar.get_value("orders", [])
                if o.status == "completed"]
