"""Order creation, assignment (nearest rider first) and dispatching."""

import logging
import math

import globalvar
import system
from order_model import Order
from path_planner import PathPlanner

logger = logging.getLogger(__name__)


def rider_distance(rider, pos):
    """Euclidean distance between a rider and a point."""
    return math.sqrt((rider.x - pos[0]) ** 2 + (rider.y - pos[1]) ** 2)


def _is_idle(rider):
    return rider.state == 0 and not rider.orders


def find_best_rider_for_order(order):
    """Return the best rider for ``order`` (closest to the restaurant).

    If the number of pending orders exceeds the number of idle riders and
    funds allow, a new rider is recruited first.  Idle riders are preferred;
    if none is idle, the closest rider overall (fewest orders on ties) is
    chosen.  Returns None if there are no riders at all.
    """
    system.ensure_initialized()
    riders = globalvar.get_value("riders", [])
    orders = globalvar.get_value("orders", []) or []
    idle = [r for r in riders if _is_idle(r)]
    pending = [o for o in orders if getattr(o, "status", None) == "pending"]
    pending_count = len(pending)
    if order not in pending and getattr(order, "status", "pending") == "pending":
        pending_count += 1
    recruited = False
    if pending_count > len(idle):
        new_rider = system.recruit_rider()
        if new_rider is not None:
            idle.append(new_rider)
            recruited = True
    globalvar.set_value("last_recruited", recruited)
    candidates = idle or list(riders)
    if not candidates:
        return None
    pos = order.res_pos
    return min(candidates,
               key=lambda r: (rider_distance(r, pos), len(r.orders), r.rider_id))


class OrderManager:
    """Handles order creation, assignment and completion bookkeeping."""

    assignment_strategy = "nearest"

    @property
    def orders(self):
        return globalvar.get_value("orders", []) or []

    def create_order(self, coords):
        """Create an order from ``[rx, ry, cx, cy]``."""
        if coords is None or len(coords) != 4:
            raise ValueError("Exactly four coordinates are required")
        return Order(tuple(coords[:2]), tuple(coords[2:]))

    def assign(self, order):
        """Assign ``order`` to the best rider; returns (rider, recruited)."""
        rider = find_best_rider_for_order(order)
        recruited = bool(globalvar.get_value("last_recruited", False))
        if rider is not None:
            order.assign_to(rider.rider_id)
        return rider, recruited

    def place_order(self, coords):
        """Create and assign an order; returns a result dictionary."""
        order = self.create_order(coords)
        rider = find_best_rider_for_order(order)
        recruited = bool(globalvar.get_value("last_recruited", False))
        route = None
        if rider is not None:
            previous = [o for o in rider.orders if o.status != "completed"]
            start = (rider.x, rider.y) if not previous else previous[-1].cus_pos
            order.assign_to(rider.rider_id)
            route = PathPlanner.plan_multi(start, [order.res_pos, order.cus_pos],
                                           rider.speed)
        return {"order": order, "rider": rider, "recruited": recruited,
                "route": route}

    def dispatch_pending(self):
        """Try to assign every pending (unassigned) order."""
        for order in list(self.orders):
            if order.status == "pending" and order.rider_id is None:
                rider = find_best_rider_for_order(order)
                if rider is not None:
                    order.assign_to(rider.rider_id)

    def completed_orders(self):
        return [o for o in self.orders if o.status == "completed"]

    def active_orders(self):
        return [o for o in self.orders if o.status != "completed"]
