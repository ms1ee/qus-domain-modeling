"""Order creation, assignment and completion handling."""

import logging
import math

import globalvar
import system
from order_model import Order

logger = logging.getLogger(__name__)


def _distance(rider, order):
    return math.hypot(rider.x - order.res_x, rider.y - order.res_y)


def find_best_rider_for_order(order):
    """Return the best rider for ``order`` (closest by Euclidean distance).

    Idle riders are preferred; if none are idle, the least loaded rider
    (then closest) is chosen. Returns None when there are no riders.
    """
    riders = globalvar.get_value("riders", []) or []
    if not riders:
        return None
    idle = [r for r in riders if r.state == 0 and not r.orders]
    if idle:
        return min(idle, key=lambda r: (_distance(r, order), r.rider_id))
    return min(riders, key=lambda r: (len(r.orders), _distance(r, order), r.rider_id))


def assign_order(order, rider):
    """Assign ``order`` to ``rider``."""
    order.assign_distance = round(_distance(rider, order), 2)
    order.assign_to(rider.rider_id)
    rider.orders.append(order)
    logger.info("Order %s assigned to rider %s", order.id, rider.rider_id)


def dispatch_pending_orders():
    """Try to assign every unassigned pending order. Returns assigned count."""
    unassigned = [o for o in (globalvar.get_value("orders") or [])
                  if o.status == "pending" and o.rider_id is None]
    if not unassigned:
        return 0
    system.check_recruitment()
    count = 0
    for order in unassigned:
        rider = find_best_rider_for_order(order)
        if rider is not None:
            assign_order(order, rider)
            count += 1
    return count


class OrderManager:
    """Handles order creation, assignment and completion statistics."""

    def create_order(self, coords):
        """Create and dispatch an order from ``[rx, ry, cx, cy]``.

        Returns ``(order, rider, recruited_riders)``; rider may be None.
        """
        rx, ry, cx, cy = [int(v) for v in coords]
        order = Order((rx, ry), (cx, cy))
        recruited = system.check_recruitment()
        rider = find_best_rider_for_order(order)
        if rider is not None:
            assign_order(order, rider)
        else:
            logger.warning("Order %s waiting: no rider available", order.id)
        return order, rider, recruited

    @staticmethod
    def all_orders():
        """Return all orders."""
        return list(globalvar.get_value("orders") or [])

    @staticmethod
    def completed_orders():
        """Return completed orders."""
        return [o for o in OrderManager.all_orders() if o.status == "completed"]

    @staticmethod
    def statistics():
        """Return delivery efficiency statistics."""
        done = OrderManager.completed_orders()
        total = len(OrderManager.all_orders())
        if not done:
            return {"total": total, "completed": 0, "avg_time": None}
        avg = sum(o.time_taken for o in done) / float(len(done))
        return {"total": total, "completed": len(done), "avg_time": round(avg, 2)}
