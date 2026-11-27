"""Order creation, assignment and completion handling."""

import logging

import globalvar
from order_model import Order
from path_planner import PathPlanner, MAP_MIN, MAP_MAX
from rider import IDLE

logger = logging.getLogger(__name__)


def _distance(rider, order):
    return PathPlanner.euclidean((rider.x, rider.y), order.res_pos)


def find_best_rider_for_order(order):
    """Return the rider closest (Euclidean) to the order's restaurant.

    Idle riders are preferred; if none is idle the closest rider overall
    (with the fewest orders as tie breaker) is returned.  Returns None if
    there are no riders.
    """
    riders = globalvar.get_value("riders") or []
    if not riders:
        return None
    idle = [r for r in riders if r.state == IDLE and not r.orders]
    candidates = idle if idle else riders
    return min(candidates,
               key=lambda r: (_distance(r, order), len(r.orders), r.rider_id))


class OrderManager:
    """Handles order creation, assignment and completion tracking."""

    @staticmethod
    def validate_coords(coords):
        """Validate 4 integer coordinates in range 0-800."""
        if len(coords) != 4:
            raise ValueError("exactly 4 coordinates required")
        result = []
        for c in coords:
            if isinstance(c, bool) or not isinstance(c, int):
                raise ValueError("coordinates must be integers")
            if not MAP_MIN <= c <= MAP_MAX:
                raise ValueError("coordinates must be within 0-800")
            result.append(c)
        return result

    @staticmethod
    def assign(order):
        """Assign ``order`` to the best rider; returns rider or None."""
        rider = find_best_rider_for_order(order)
        if rider is None:
            return None
        rider.orders.append(order)
        order.assign_to(rider.rider_id)
        return rider

    @staticmethod
    def create_order(coords):
        """Create and assign an order; returns a result dict."""
        from system import SystemManager
        SystemManager.ensure_initialized()
        rx, ry, cx, cy = OrderManager.validate_coords(list(coords))
        order = Order((rx, ry), (cx, cy))
        globalvar.get_value("orders").append(order)
        pending = globalvar.get_value("pending_orders")
        new_rider = SystemManager.auto_recruit(len(pending) + 1)
        rider = OrderManager.assign(order)
        if rider is None:
            pending.append(order)
        return {"order": order, "rider": rider, "new_rider": new_rider}

    @staticmethod
    def process_pending():
        """Try to assign queued orders (and recruit if needed)."""
        from system import SystemManager
        pending = globalvar.get_value("pending_orders") or []
        if not pending:
            return []
        SystemManager.auto_recruit(len(pending))
        assigned = []
        for order in list(pending):
            rider = OrderManager.assign(order)
            if rider is None:
                break
            pending.remove(order)
            assigned.append(order)
        return assigned

    @staticmethod
    def all_orders():
        return globalvar.get_value("orders") or []

    @staticmethod
    def completed_orders():
        return [o for o in OrderManager.all_orders() if o.status == "completed"]

    @staticmethod
    def efficiency():
        """Average delivery time of completed orders (None if none)."""
        done = OrderManager.completed_orders()
        if not done:
            return None
        return sum(o.time_taken for o in done) / len(done)
