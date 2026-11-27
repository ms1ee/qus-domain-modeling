"""Order creation, assignment and completion handling."""

import logging

import globalvar
import resources
from grid_map import MAP_SIZE
from order_model import Order
from path_planner import PathPlanner

logger = logging.getLogger(__name__)

_planner = PathPlanner()


def _distance_to_restaurant(rider, order):
    return _planner.distance(rider.projected_position(exclude=order), order.res_pos)


def find_best_rider_for_order(order):
    """Select the best rider for ``order``.

    1. Nearest idle rider (street distance to the restaurant).
    2. Otherwise recruit a new rider if funds allow.
    3. Otherwise the busy rider who can reach the restaurant soonest
       (queued workload + distance), balancing load.
    Returns the Rider or None if no rider exists at all.
    """
    riders = globalvar.get_value("riders") or []
    idle = [r for r in riders if r.is_available()]
    if idle:
        return min(idle, key=lambda r: (_distance_to_restaurant(r, order), r.rider_id))
    new_rider = resources.recruit_rider()
    if new_rider is not None:
        return new_rider
    if not riders:
        return None

    def cost(r):
        work, pos = r.workload(exclude=order)
        return (work + _planner.distance(pos, order.res_pos),
                len(r.pending_orders()), r.rider_id)
    return min(riders, key=cost)


class InvalidOrderError(ValueError):
    """Raised for invalid order input."""


class OrderManager:
    """Handles creation, assignment and completion of orders."""

    def __init__(self, planner=None):
        self.planner = planner or PathPlanner()

    @property
    def order_id_counter(self):
        return Order._id_counter

    @staticmethod
    def orders():
        lst = globalvar.get_value("orders")
        if lst is None:
            lst = []
            globalvar.set_value("orders", lst)
        return lst

    @staticmethod
    def validate(coords):
        """Validate four integer coordinates in range 0..800."""
        if len(coords) != 4:
            raise InvalidOrderError("Exactly four coordinates are required.")
        values = []
        for c in coords:
            if isinstance(c, bool):
                raise InvalidOrderError("Coordinates must be integers.")
            try:
                v = int(c)
            except (TypeError, ValueError):
                raise InvalidOrderError("Coordinates must be integers.")
            if isinstance(c, float) and c != v:
                raise InvalidOrderError("Coordinates must be integers.")
            if not 0 <= v <= MAP_SIZE:
                raise InvalidOrderError(
                    "Coordinate %d out of range (0-%d)." % (v, MAP_SIZE))
            values.append(v)
        return values

    def create_order(self, coords):
        """Create and assign an order.

        Returns (order, rider_or_None, new_rider_added: bool).
        """
        rx, ry, cx, cy = self.validate(coords)
        order = Order((rx, ry), (cx, cy))
        self.orders().append(order)
        before = len(globalvar.get_value("riders") or [])
        rider = find_best_rider_for_order(order)
        after = len(globalvar.get_value("riders") or [])
        if rider is None:
            order.status = "unassigned"
            logger.warning("Order %d could not be assigned", order.id)
        else:
            self.assign(order, rider)
        return order, rider, after > before

    @staticmethod
    def assign(order, rider):
        """Assign ``order`` to ``rider``."""
        order.assign_to(rider.rider_id)
        if order not in rider.orders:
            rider.orders.append(order)

    def retry_unassigned(self):
        """Try to assign orders that previously found no rider."""
        assigned = []
        for order in self.orders():
            if order.status == "unassigned":
                rider = find_best_rider_for_order(order)
                if rider is not None:
                    self.assign(order, rider)
                    assigned.append((order, rider))
        return assigned

    def completed_orders(self):
        return [o for o in self.orders() if o.status == "completed"]

    def active_orders(self):
        return [o for o in self.orders() if o.status != "completed"]

    def get_order(self, order_id):
        for o in self.orders():
            if o.id == order_id:
                return o
        return None
