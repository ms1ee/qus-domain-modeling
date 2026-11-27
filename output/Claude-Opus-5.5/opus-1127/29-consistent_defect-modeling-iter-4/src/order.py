"""Order management: creation, assignment and completion."""

import globalvar
import system
from order_model import Order
from path_planner import euclidean


def find_best_rider_for_order(order):
    """Return the best rider for ``order``.

    Riders with the fewest active orders are preferred; ties are broken by
    the straight-line distance to the restaurant, then by rider id.
    If no rider exists, one is recruited when funds allow.
    """
    riders = globalvar.get_value("riders") or []
    if not riders:
        cfg = globalvar.get_value("config") or system.DEFAULT_CONFIG
        funds = globalvar.get_value("funds")
        if funds is None or funds >= int(cfg.get("recruitment_threshold",
                                                 300)):
            system.recruit_rider()
        riders = globalvar.get_value("riders") or []
    if not riders:
        return None
    res = tuple(order.res_pos)
    return min(riders, key=lambda r: (len(r.active_orders()),
                                      euclidean((r.x, r.y), res),
                                      r.rider_id))


class OrderManager:
    """Handles order creation, assignment and completion queries."""

    def create_order(self, res_pos, cus_pos):
        """Create and assign an order.

        Returns a dict with keys ``order``, ``rider`` and ``recruited``
        (the new Rider or None).
        """
        order = Order(res_pos, cus_pos)
        recruited = system.check_and_recruit()
        rider = find_best_rider_for_order(order)
        if rider is not None:
            order.assign_to(rider.rider_id)
            if not any(o is order for o in rider.orders):
                rider.orders.append(order)
        return {"order": order, "rider": rider, "recruited": recruited}

    @staticmethod
    def all_orders():
        return list(globalvar.get_value("orders") or [])

    @staticmethod
    def completed_orders():
        return [o for o in OrderManager.all_orders() if o.completed]
