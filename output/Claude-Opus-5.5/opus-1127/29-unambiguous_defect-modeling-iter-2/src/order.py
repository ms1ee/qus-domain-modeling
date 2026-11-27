"""Order creation, assignment (distance-first) and bookkeeping."""

import logging

import globalvar
import system
from order_model import Order
from path_planner import PathPlanner, Route

logger = logging.getLogger(__name__)

_planner = PathPlanner()


def rider_distance_to_order(rider, order, from_queue_end=False):
    """Street distance from the rider to the order's restaurant."""
    start = rider.final_position() if from_queue_end else (rider.x, rider.y)
    return _planner.best_access_point(start, order.res_pos)[1]


def find_best_rider_for_order(order):
    """Select the most suitable rider for ``order``.

    1. The nearest idle rider (street distance), ties broken by id.
    2. Otherwise a newly recruited rider if funds allow.
    3. Otherwise the least loaded rider, then the nearest queue end.
    4. With no riders at all, a rider is force-recruited.

    The order is not appended; the caller appends it to ``rider.orders``.
    """
    riders = globalvar.get_value("riders")
    if riders is None:
        riders = []
        globalvar.set_value("riders", riders)
    available = [r for r in riders if r.is_available()]
    if available:
        return min(available,
                   key=lambda r: (rider_distance_to_order(r, order),
                                  r.rider_id))
    new_rider = system.try_recruit_rider()
    if new_rider is not None:
        return new_rider
    if riders:
        return min(riders,
                   key=lambda r: (len(r.pending_orders()),
                                  rider_distance_to_order(r, order, True),
                                  r.rider_id))
    logger.warning("No riders and insufficient funds; forcing recruitment")
    return system.recruit_rider(force=True)


class OrderManager:
    """Handles order creation, assignment and completion statistics."""

    def __init__(self, planner=None):
        self.planner = planner or _planner

    @property
    def orders(self):
        """All orders known to the system."""
        orders = globalvar.get_value("orders")
        if orders is None:
            orders = []
            globalvar.set_value("orders", orders)
        return orders

    def create_order(self, coords):
        """Create and register an order from ``[rx, ry, cx, cy]``."""
        if len(coords) != 4:
            raise ValueError("exactly four coordinates are required")
        order = Order((coords[0], coords[1]), (coords[2], coords[3]))
        self.orders.append(order)
        return order

    def preview_route(self, rider, order):
        """Planned route rider -> restaurant -> customer."""
        if rider.pending_orders():
            start = rider.final_position()
        else:
            start = (rider.x, rider.y)
        pickup, _ = self.planner.best_access_point(start, order.res_pos)
        dropoff, _ = self.planner.best_access_point(pickup, order.cus_pos)
        first = self.planner.plan_path(start, pickup)
        second = self.planner.plan_path(pickup, dropoff)
        waypoints = PathPlanner.simplify(first + second[1:])
        return Route(waypoints, rider.speed), pickup, dropoff

    def assign_order(self, order):
        """Assign ``order`` to the best rider.

        :return: (rider, recruited: bool)
        """
        before = globalvar.get_value("rider_id_counter", 0) or 0
        rider = find_best_rider_for_order(order)
        recruited = (globalvar.get_value("rider_id_counter", 0) or 0) > before
        order.assign_to(rider.rider_id)
        rider.orders.append(order)
        return rider, recruited

    def submit(self, coords):
        """Create, assign and preview an order.

        :return: dict with keys order, rider, recruited, route, pickup,
            dropoff, queue_position.
        """
        order = self.create_order(coords)
        before = globalvar.get_value("rider_id_counter", 0) or 0
        rider = find_best_rider_for_order(order)
        recruited = (globalvar.get_value("rider_id_counter", 0) or 0) > before
        route, pickup, dropoff = self.preview_route(rider, order)
        order.assign_to(rider.rider_id)
        rider.orders.append(order)
        return {
            "order": order,
            "rider": rider,
            "recruited": recruited,
            "route": route,
            "pickup": pickup,
            "dropoff": dropoff,
            "queue_position": len(rider.pending_orders()),
        }

    def completed_orders(self):
        """Orders already delivered."""
        return [o for o in self.orders if o.completed]

    def active_orders(self):
        """Orders not yet delivered."""
        return [o for o in self.orders if not o.completed]

    def statistics(self):
        """Delivery efficiency summary."""
        done = self.completed_orders()
        times = [o.time_taken for o in done if o.time_taken is not None]
        return {
            "total": len(self.orders),
            "completed": len(done),
            "active": len(self.orders) - len(done),
            "average_time": round(sum(times) / len(times), 2) if times else None,
        }
