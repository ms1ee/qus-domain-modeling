"""Order management: creation, assignment and completion tracking."""

import logging

import globalvar
from order_model import Order
from path_planner import PathPlanner

logger = logging.getLogger(__name__)


def _rider_distance(rider, order):
    """Euclidean distance between a rider and the order's restaurant."""
    rx, ry = order.res_pos
    return ((rider.x - rx) ** 2 + (rider.y - ry) ** 2) ** 0.5


def _is_idle(rider):
    if hasattr(rider, "is_idle"):
        return rider.is_idle()
    return rider.state == 0 and not rider.orders


def find_best_rider_for_order(order, riders=None):
    """Return the best rider for ``order`` (closest rider first).

    Idle riders are preferred; if none are idle, the closest rider overall
    is chosen (ties broken by fewer assigned orders, then by id).
    Returns None when there are no riders.
    """
    if riders is None:
        riders = globalvar.get_value("riders") or []
    if not riders:
        return None
    idle = [r for r in riders if _is_idle(r)]
    candidates = idle if idle else list(riders)
    return min(candidates,
               key=lambda r: (_rider_distance(r, order), len(r.orders),
                              r.rider_id))


class OrderManager:
    """Handles order creation, assignment and completion bookkeeping."""

    def __init__(self, system=None):
        self.system = system

    @staticmethod
    def all_orders():
        """List of every order created."""
        orders = globalvar.get_value("orders")
        if orders is None:
            orders = []
            globalvar.set_value("orders", orders)
        return orders

    def create_order(self, coords):
        """Create an order from [rx, ry, cx, cy] and register it."""
        order = Order((coords[0], coords[1]), (coords[2], coords[3]))
        self.all_orders().append(order)
        logger.info("Created %r", order)
        return order

    def pending_orders(self):
        """Orders not yet assigned to any rider."""
        return [o for o in self.all_orders() if o.status == "pending"]

    def completed_orders(self):
        """Orders that have been delivered."""
        return [o for o in self.all_orders() if o.status == "completed"]

    @staticmethod
    def assign_order(order, riders=None):
        """Assign ``order`` to the best rider; returns the rider or None."""
        rider = find_best_rider_for_order(order, riders)
        if rider is None:
            return None
        rider.orders.append(order)
        order.assign_to(rider.rider_id)
        logger.info("Order %d assigned to rider %s", order.id, rider.rider_id)
        return rider

    def assign_pending(self):
        """Try to assign every pending order; returns list of (order, rider)."""
        result = []
        for order in self.pending_orders():
            rider = self.assign_order(order)
            if rider is None:
                break
            result.append((order, rider))
        return result

    def dispatch(self, coords):
        """Full order intake: create, auto-recruit, assign.

        Returns a dict with keys ``order``, ``rider`` (or None),
        ``new_riders`` (list) and ``route`` (waypoints or []).
        """
        order = self.create_order(coords)
        new_riders = []
        if self.system is not None:
            new_riders = self.system.auto_recruit()
        rider = self.assign_order(order)
        route = rider.planned_route() if rider is not None else []
        return {"order": order, "rider": rider, "new_riders": new_riders,
                "route": route,
                "route_length": PathPlanner.route_length(route) if route else 0}
