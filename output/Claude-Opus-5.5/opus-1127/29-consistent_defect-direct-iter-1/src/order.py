"""Order creation, assignment and completion handling."""

import globalvar
from order_model import Order
from path_planner import PathPlanner
from rider import Rider, IDLE

RECRUIT_COST = 500
RECRUIT_THRESHOLD = 300


def hire_rider():
    """Create a new rider, deduct the recruitment cost and register it."""
    counter = (globalvar.get_value("rider_id_counter", 0) or 0) + 1
    globalvar.set_value("rider_id_counter", counter)
    rider = Rider(counter)
    riders = globalvar.get_value("riders")
    if riders is None:
        riders = []
        globalvar.set_value("riders", riders)
    riders.append(rider)
    funds = globalvar.get_value("funds", 0) or 0
    globalvar.set_value("funds", funds - RECRUIT_COST)
    return rider


def find_best_rider_for_order(order):
    """Return the best rider for ``order``.

    Riders with the fewest active orders are preferred; ties are broken by
    the distance sqrt((rx-res_x)^2 + (ry-res_y)^2) to the restaurant, then by
    rider id. If no rider exists, one is recruited.
    """
    riders = globalvar.get_value("riders") or []
    if not riders:
        return hire_rider()
    res = order.res_pos

    def key(r):
        return (len(r.active_orders()),
                PathPlanner.euclidean((r.x, r.y), res),
                r.rider_id)

    return min(riders, key=key)


class OrderManager:
    """Handles order creation, recruitment, assignment and queries."""

    def all_orders(self):
        orders = globalvar.get_value("orders")
        if orders is None:
            orders = []
            globalvar.set_value("orders", orders)
        return orders

    def pending_orders(self):
        return [o for o in self.all_orders() if o.status == "pending"]

    @staticmethod
    def idle_riders():
        return [r for r in (globalvar.get_value("riders") or [])
                if r.state == IDLE and not r.active_orders()]

    def check_recruitment(self):
        """Recruit riders while funds allow and pending orders exceed idle riders."""
        hired = []
        while ((globalvar.get_value("funds", 0) or 0) >= RECRUIT_THRESHOLD
               and len(self.pending_orders()) > len(self.idle_riders())):
            hired.append(hire_rider())
        return hired

    def assign(self, order):
        """Assign ``order`` to the best rider and return that rider."""
        rider = find_best_rider_for_order(order)
        rider.orders.append(order)
        order.assign_to(rider.rider_id)
        return rider

    def create_order(self, res_pos, cus_pos):
        """Create, register and assign an order.

        Returns a dict with keys: order, rider, new_rider (bool), route,
        distance, estimated_time.
        """
        order = Order(res_pos, cus_pos)
        self.all_orders().append(order)
        hired = self.check_recruitment()
        rider = self.assign(order)
        # Route: from the point where the rider becomes free to the customer.
        active = rider.active_orders()
        start = (rider.x, rider.y)
        targets = []
        if len(active) > 1:
            prev = active[-2]
            targets_prev = []
            if prev.status != "picked_up":
                targets_prev.append(prev.res_pos)
            targets_prev.append(prev.cus_pos)
            # full chain of queued orders
            for o in active[:-1]:
                if o.status != "picked_up":
                    targets.append(o.res_pos)
                targets.append(o.cus_pos)
        targets.extend([order.res_pos, order.cus_pos])
        route, _ = PathPlanner.plan_multi(start, targets)
        distance = PathPlanner.path_length(route)
        speed = max(1, rider.speed)
        est = -(-distance // speed)
        return {
            "order": order,
            "rider": rider,
            "new_rider": bool(hired),
            "hired": hired,
            "route": route,
            "distance": distance,
            "estimated_time": est,
        }
