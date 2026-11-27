"""Order management: creation, assignment and completion queries."""

import globalvar
from order_model import Order, STATUS_COMPLETED
from path_planner import PathPlanner
from rider import STATE_IDLE
from system import SystemManager


def find_best_rider_for_order(order):
    """Return the best rider for ``order`` (closest rider first).

    Idle riders are preferred, chosen by distance to the restaurant. If
    all riders are busy, the rider with the fewest queued orders wins
    (load balancing), ties broken by distance from where the rider will
    finish. If no riders exist, one is recruited.
    """
    riders = globalvar.get_value("riders")
    if riders is None:
        riders = []
        globalvar.set_value("riders", riders)
    if not riders:
        return SystemManager().recruit_rider(force=True)

    res = order.res_pos
    idle = [r for r in riders if r.state == STATE_IDLE and not r.orders]
    if idle:
        return min(idle, key=lambda r: (PathPlanner.manhattan(r.position, res),
                                        r.rider_id))
    return min(riders, key=lambda r: (len(r.orders),
                                      PathPlanner.manhattan(r.projected_position(), res),
                                      r.rider_id))


class OrderManager:
    """Handles order creation, assignment and completion records."""

    def __init__(self, system=None):
        self.system = system or SystemManager()

    @property
    def orders(self):
        return globalvar.get_value("orders")

    def create_order(self, rx, ry, cx, cy):
        """Create a new Order from raw coordinates."""
        return Order((rx, ry), (cx, cy))

    def assign_order(self, order):
        """Assign an order to the best rider.

        Returns ``(rider, new_rider)`` where new_rider is the rider that was
        recruited during this assignment (or None).
        """
        new_rider = self.system.check_recruit()
        rider = find_best_rider_for_order(order)
        if rider is None:
            rider = self.system.recruit_rider(force=True)
            new_rider = rider
        rider.orders.append(order)
        order.assign_to(rider.rider_id)
        self.orders.append(order)
        return rider, new_rider

    def planned_route(self, rider, order):
        """Plan the route the rider will take for ``order``.

        Returns ``(start, waypoints, pickup_len, delivery_len, queued)``.
        """
        idx = rider.orders.index(order) if order in rider.orders else len(rider.orders)
        queued = idx
        if idx == 0:
            start = rider.position
        else:
            start = tuple(rider.orders[idx - 1].cus_pos)
        waypoints, lengths = PathPlanner.plan_route(start, [order.res_pos, order.cus_pos])
        return start, waypoints, lengths[0], lengths[1], queued

    def get_order(self, order_id):
        """Find an order by id."""
        for o in self.orders:
            if o.id == order_id:
                return o
        return None

    def completed_orders(self):
        """List of completed orders."""
        return [o for o in self.orders if o.status == STATUS_COMPLETED]

    def active_orders(self):
        """List of orders not yet completed."""
        return [o for o in self.orders if o.status != STATUS_COMPLETED]
