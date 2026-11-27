"""Order management: creation, assignment and completion tracking."""

import logging

import globalvar
from grid_map import CELL_SIZE, MAP_SIZE
from order_model import Order
from path_planner import PathPlanner
from rider import IDLE, PICKING_UP

logger = logging.getLogger(__name__)

_PLANNER = PathPlanner(CELL_SIZE, MAP_SIZE)


def _active_orders(rider):
    return [o for o in rider.orders if getattr(o, "status", "") != "completed"]


def find_best_rider_for_order(order, riders=None):
    """Return the best rider for ``order`` (closest rider first).

    Idle riders are preferred and ranked by street distance to the restaurant.
    If all riders are busy, the rider with the smallest workload (and then the
    shortest distance from its last drop-off) wins, which balances load.
    Returns None if there are no riders.
    """
    if riders is None:
        riders = globalvar.get_value("riders") or []
    if not riders:
        return None
    target = order.restaurant

    idle = [r for r in riders if r.state == IDLE and not _active_orders(r)]
    if idle:
        def idle_key(r):
            manhattan = abs(r.x - target[0]) + abs(r.y - target[1])
            return (_PLANNER.distance((r.x, r.y), target), manhattan, r.rider_id)
        return min(idle, key=idle_key)

    def busy_key(r):
        active = _active_orders(r)
        start = active[-1].customer if active else (r.x, r.y)
        return (len(active), _PLANNER.distance(start, target), r.rider_id)
    return min(riders, key=busy_key)


class OrderManager:
    """Handles order creation, assignment and bookkeeping."""

    def __init__(self, planner=None):
        self.planner = planner or PathPlanner(CELL_SIZE, MAP_SIZE)
        if globalvar.get_value("orders") is None:
            globalvar.set_value("orders", [])
        if globalvar.get_value("pending_orders") is None:
            globalvar.set_value("pending_orders", [])

    @staticmethod
    def all_orders():
        return globalvar.get_value("orders") or []

    @staticmethod
    def pending_orders():
        return globalvar.get_value("pending_orders") or []

    def completed_orders(self):
        return [o for o in self.all_orders() if o.status == "completed"]

    @staticmethod
    def compute_fee(order):
        cfg = globalvar.get_value("config")
        base = int(cfg.get("base_fee", 20)) if cfg else 20
        per = int(cfg.get("fee_per_100", 5)) if cfg else 5
        return base + per * (order.distance // 100)

    def create_order(self, rx, ry, cx, cy):
        """Create and register an order (coordinates already validated)."""
        order = Order((rx, ry), (cx, cy))
        order.fee = self.compute_fee(order)
        orders = self.all_orders()
        orders.append(order)
        globalvar.set_value("orders", orders)
        pending = self.pending_orders()
        pending.append(order)
        globalvar.set_value("pending_orders", pending)
        logger.debug("Created %r", order)
        return order

    def assign_order(self, order):
        """Assign an order to the best rider; returns the rider or None."""
        rider = find_best_rider_for_order(order)
        if rider is None:
            return None
        order.assign_to(rider.rider_id)
        rider.orders.append(order)
        pending = self.pending_orders()
        if order in pending:
            pending.remove(order)
        logger.debug("Assigned order %d to rider %d", order.id, rider.rider_id)
        return rider

    def assign_pending(self):
        """Try to assign all waiting orders; returns list of (order, rider)."""
        results = []
        for order in list(self.pending_orders()):
            if order.status == "completed":
                self.pending_orders().remove(order)
                continue
            rider = self.assign_order(order)
            if rider is None:
                break
            results.append((order, rider))
        return results

    def planned_route_for(self, rider, order):
        """Full planned route of ``rider`` up to delivering ``order``."""
        stops = []
        cur = rider.current_order
        if cur is not None and cur.status != "completed":
            if rider.state == PICKING_UP:
                stops.append(cur.restaurant)
            stops.append(cur.customer)
        for o in rider.orders:
            if o is cur or o.status == "completed":
                continue
            stops.append(o.restaurant)
            stops.append(o.customer)
            if o is order:
                break
        if order is cur:
            pass
        elif order not in rider.orders:
            stops.extend([order.restaurant, order.customer])
        return self.planner.plan_route((rider.x, rider.y), stops, rider.speed)
