"""Order management: creation, closest-rider assignment and completion."""

import logging

import globalvar
from order_model import Order, OrderStatus
from path_planner import manhattan
from rider import RiderState

logger = logging.getLogger(__name__)


def find_best_rider_for_order(order, riders=None):
    """Return the best rider for ``order`` (closest rider first).

    Idle riders without pending work are preferred, ranked by distance to the
    restaurant. If no rider is idle, riders compete by the total distance of
    their remaining work plus the distance from their final drop-off to the
    restaurant (load balancing). Ties are broken by fewer pending orders and
    then lower rider id. Returns None if no rider exists.
    """
    if riders is None:
        riders = globalvar.get_value("riders") or []
    if not riders:
        return None
    res = order.res_pos
    idle = [r for r in riders
            if r.state == RiderState.IDLE and not r.has_pending_orders()]
    if idle:
        return min(idle, key=lambda r: (manhattan(r.position, res),
                                        len(r.pending_orders()), r.rider_id))

    def score(r):
        remaining, end = r.remaining_work()
        return (remaining + manhattan(end, res), len(r.pending_orders()),
                r.rider_id)

    return min(riders, key=score)


class OrderManager:
    """Handles order creation, assignment and bookkeeping."""

    assignment_strategy = "closest_rider_first"

    @property
    def orders(self):
        orders = globalvar.get_value("orders")
        if orders is None:
            orders = []
            globalvar.set_value("orders", orders)
        return orders

    def create_order(self, coords):
        """Create an order from ``[res_x, res_y, cus_x, cus_y]``."""
        if not isinstance(coords, (list, tuple)) or len(coords) != 4:
            raise ValueError("Order requires exactly four coordinates")
        order = Order([coords[0], coords[1]], [coords[2], coords[3]])
        self.orders.append(order)
        logger.info("Created %r", order)
        return order

    @staticmethod
    def assign_to_rider(order, rider):
        """Assign ``order`` to ``rider``."""
        if order not in rider.orders:
            rider.orders.append(order)
        order.assign_to(rider.rider_id)

    def assign_order(self, order):
        """Assign an order to the best rider; returns the rider or None."""
        rider = find_best_rider_for_order(order)
        if rider is not None:
            self.assign_to_rider(order, rider)
            logger.info("Assigned order #%d to rider #%d", order.id,
                        rider.rider_id)
        return rider

    def pending_orders(self):
        return [o for o in self.orders if o.status == OrderStatus.PENDING]

    def completed_orders(self):
        return [o for o in self.orders if o.status == OrderStatus.COMPLETED]

    def active_orders(self):
        return [o for o in self.orders if o.status != OrderStatus.COMPLETED]

    def dispatch_pending(self):
        """Try to assign every pending order. Returns [(order, rider)]."""
        result = []
        for order in self.pending_orders():
            rider = self.assign_order(order)
            if rider is None:
                break
            result.append((order, rider))
        return result
