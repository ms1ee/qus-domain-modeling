"""Order management: creation, assignment, completion bookkeeping."""

import logging
import math

import globalvar
from order_model import Order
from rider import IDLE

logger = logging.getLogger(__name__)


def _distance(rider, order):
    return math.sqrt((rider.x - order.res_pos[0]) ** 2 +
                     (rider.y - order.res_pos[1]) ** 2)


def find_best_rider_for_order(order):
    """Return the best rider: fewest active orders, then closest to restaurant."""
    riders = globalvar.get_value("riders", None)
    if riders is None:
        riders = []
        globalvar.set_value("riders", riders)
    if not riders:
        import system
        cfg = system.get_config()
        if (globalvar.get_value("funds", 0) or 0) >= cfg.get("recruit_threshold"):
            return system.recruit_rider()
        return None
    return min(riders, key=lambda r: (len(r.active_orders), _distance(r, order),
                                      r.rider_id))


class OrderManager:
    """Handles order creation, assignment and statistics."""

    def __init__(self, system_manager=None):
        self.system_manager = system_manager

    @property
    def orders(self):
        orders = globalvar.get_value("orders", None)
        if orders is None:
            orders = []
            globalvar.set_value("orders", orders)
        return orders

    def pending_count(self):
        return sum(1 for o in self.orders if o.status == "pending")

    @staticmethod
    def idle_count():
        riders = globalvar.get_value("riders", []) or []
        return sum(1 for r in riders if r.state == IDLE and not r.active_orders)

    def create_order(self, rx, ry, cx, cy):
        """Create and assign an order. Returns a result dict."""
        import system
        order = Order([rx, ry], [cx, cy])
        self.orders.append(order)
        cfg = system.get_config()
        recruited = None
        funds = globalvar.get_value("funds", 0) or 0
        if funds >= cfg.get("recruit_threshold") and \
                self.pending_count() > self.idle_count():
            recruited = system.recruit_rider()
        rider = find_best_rider_for_order(order)
        route = None
        if rider is not None:
            order.assign_to(rider.rider_id)
            rider.orders.append(order)
            route = rider.planned_route()
            order.planned_distance = route.length
        else:
            logger.warning("No rider available for order %s", order.id)
        return {"order": order, "rider": rider, "recruited": recruited,
                "route": route}

    def completed_orders(self):
        return [o for o in self.orders if o.status == "completed"]
