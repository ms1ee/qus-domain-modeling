"""Order creation, assignment and completion handling."""

import logging

import globalvar
from order_model import Order
from path_planner import planner

logger = logging.getLogger(__name__)


def _assignment_key(rider, order):
    """Sort key used to choose a rider for ``order``.

    Idle riders come first, then lower estimated cost (Manhattan distance
    to the restaurant plus pending workload), then rider id.
    """
    dist = planner.manhattan((rider.x, rider.y), order.res_pos)
    active = [o for o in rider.active_orders() if o is not order]
    workload = sum(o.distance + 200 for o in active)
    idle = rider.state == 0 and not active
    return (0 if idle else 1, dist + workload, len(active), rider.rider_id)


def find_best_rider_for_order(order):
    """Return the best rider for ``order`` (distance-first, load balanced).

    If there are no riders at all, one is recruited if funds allow.
    Returns None when no rider can be found.
    """
    riders = globalvar.get_value("riders")
    if riders is None:
        riders = []
        globalvar.set_value("riders", riders)
    if not riders:
        from system import SystemManager
        SystemManager().recruit_rider()
        riders = globalvar.get_value("riders") or []
    if not riders:
        return None
    return min(riders, key=lambda r: _assignment_key(r, order))


class OrderManager:
    """Handles order creation, assignment and completion."""

    def __init__(self, system_manager=None):
        """Bind to a SystemManager (created lazily if not given)."""
        if system_manager is None:
            from system import SystemManager
            system_manager = SystemManager()
        self.system = system_manager

    @property
    def orders(self):
        """All orders ever created."""
        return globalvar.get_value("orders") or []

    @property
    def pending(self):
        """Orders waiting for a rider."""
        pending = globalvar.get_value("pending_orders")
        if pending is None:
            pending = []
            globalvar.set_value("pending_orders", pending)
        return pending

    @staticmethod
    def assign(order, rider):
        """Assign ``order`` to ``rider``."""
        if not any(o is order for o in rider.orders):
            rider.orders.append(order)
        order.assign_to(rider.rider_id)

    def _route_start(self, rider, order):
        """Where the rider will start the leg for ``order``."""
        prior = [o for o in rider.active_orders() if o is not order]
        if not prior:
            return (rider.x, rider.y)
        return planner.best_access((rider.x, rider.y), prior[-1].cus_pos)[0]

    def create_order(self, coords):
        """Create and assign an order from ``[rx, ry, cx, cy]``.

        :return: dict with ``order``, ``rider``, ``new_rider``, ``route``,
                 ``queued_behind`` and ``eta``.
        """
        rx, ry, cx, cy = [int(v) for v in coords]
        new_rider = None
        if self.system.needs_rider() and self.system.can_recruit():
            new_rider = self.system.recruit_rider()
        order = Order((rx, ry), (cx, cy))
        rider = find_best_rider_for_order(order)
        if new_rider is None and rider is not None and \
                len(self.system.riders) and \
                rider.log and rider.log[0]["time"] == self.system.time and \
                len(rider.log) == 1 and rider.rider_id == \
                globalvar.get_value("rider_id_counter") and \
                len(self.system.riders) == 1:
            new_rider = rider
        result = {"order": order, "rider": rider, "new_rider": new_rider,
                  "route": None, "queued_behind": 0, "eta": None}
        if rider is None:
            self.pending.append(order)
            logger.info("Order %s queued: no rider available", order.id)
            return result
        result["queued_behind"] = len([o for o in rider.active_orders()
                                       if o is not order])
        start = self._route_start(rider, order)
        self.assign(order, rider)
        route = planner.plan_order_route(start, order.res_pos, order.cus_pos)
        result["route"] = route
        speed = max(1, rider.speed)
        result["eta"] = -(-route["total"] // speed)
        return result

    def process_pending(self):
        """Try to assign queued orders. Returns number assigned."""
        assigned = 0
        for order in list(self.pending):
            if self.system.needs_rider() and self.system.can_recruit():
                self.system.recruit_rider()
            rider = find_best_rider_for_order(order)
            if rider is None:
                break
            self.assign(order, rider)
            self.pending.remove(order)
            assigned += 1
        return assigned

    def completed_orders(self):
        """All completed orders."""
        return [o for o in self.orders if o.status == "completed"]
