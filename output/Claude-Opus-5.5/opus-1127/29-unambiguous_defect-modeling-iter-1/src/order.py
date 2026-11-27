"""Order management: creation, assignment and completion tracking."""

import logging

import globalvar
import system
from order_model import Order
from path_planner import PathPlanner, Route, manhattan
from rider import RiderState

logger = logging.getLogger(__name__)


def _is_idle(rider):
    return rider.state == RiderState.IDLE and not rider.orders


def select_rider(order):
    """Select the best rider for ``order``.

    Strategy (distance-first):
    1. nearest idle rider (Manhattan distance to the restaurant);
    2. otherwise recruit a new rider if funds allow;
    3. otherwise the busy rider with the fewest queued orders, ties broken
       by distance from its final destination to the restaurant;
    4. with no riders at all and no funds, a rider is force-recruited.

    Returns ``(rider, recruited)``.
    """
    riders = globalvar.get_value("riders")
    if riders is None:
        system.init_system()
        riders = globalvar.get_value("riders")
    res = tuple(order.res_pos)
    idle = [r for r in riders if _is_idle(r)]
    if idle:
        best = min(idle, key=lambda r: (manhattan(r.position, res), r.rider_id))
        return best, False
    new_rider = system.recruit_rider()
    if new_rider is not None:
        return new_rider, True
    if riders:
        best = min(riders, key=lambda r: (len(r.orders),
                                          manhattan(r.final_destination(), res),
                                          r.rider_id))
        return best, False
    return system.recruit_rider(force=True), True


def find_best_rider_for_order(order):
    """Return the most suitable Rider for ``order`` (may recruit one)."""
    return select_rider(order)[0]


class OrderManager:
    """Handles order creation, assignment and completion queries."""

    def __init__(self):
        self.planner = PathPlanner()

    @staticmethod
    def create_order(values):
        """Create an Order from ``[rx, ry, cx, cy]``."""
        if len(values) != 4:
            raise ValueError("An order needs exactly 4 coordinates")
        return Order((values[0], values[1]), (values[2], values[3]))

    def dispatch(self, values):
        """Create and assign an order; return a dispatch result dict."""
        order = self.create_order(values)
        rider, recruited = select_rider(order)
        start = rider.final_destination() if rider.orders else rider.position
        order.assign_to(rider.rider_id)
        rider.orders.append(order)
        waypoints = self.planner.plan_multi([start, order.res_pos, order.cus_pos])
        route = Route(start, waypoints, rider.speed)
        logger.info("Order %d assigned to rider %d", order.id, rider.rider_id)
        return {
            "order": order,
            "rider": rider,
            "recruited": recruited,
            "route": route,
            "special_case": self.planner.special_case,
            "funds": globalvar.get_value("funds", 0),
        }

    @staticmethod
    def all_orders():
        return list(globalvar.get_value("orders", []) or [])

    def completed_orders(self):
        return [o for o in self.all_orders() if o.status == "completed"]

    def active_orders(self):
        return [o for o in self.all_orders() if o.status != "completed"]
