"""Order assignment: rider selection, route building, and pending queue."""

import logging

import config
import globalvar
from order_model import Order
from path_planner import PathPlanner
from system import SystemManager

logger = logging.getLogger(__name__)


class NoRiderAvailableError(RuntimeError):
    """Raised when no rider exists and none can be recruited."""


def find_best_rider_for_order(order):
    """Select the best rider for an order.

    The score is the Manhattan distance from the rider to the restaurant plus
    a load penalty for each order the rider already holds. The distance term
    dominates for nearby riders, while the load penalty balances work across
    riders. Ties are broken by rider ID.

    Args:
        order: The Order to assign.

    Returns:
        The selected Rider.

    Raises:
        NoRiderAvailableError: If there are no riders.
    """
    riders = globalvar.get_value("riders") or []
    if not riders:
        raise NoRiderAvailableError("no riders are available")
    penalty = config.setting("load_penalty")

    def score(rider):
        distance = PathPlanner.manhattan(rider.position, order.res_pos)
        return (distance + penalty * len(rider.orders), rider.rider_id)

    best = min(riders, key=score)
    logger.debug("Order %d matched to rider %d", order.id, best.rider_id)
    return best


class OrderManager:
    """Create, assign, queue, and report on orders."""

    def __init__(self, system=None):
        """Create the manager.

        Args:
            system: Optional SystemManager; a default one is created if omitted.
        """
        self.system = system if system is not None else SystemManager()
        self.pending = []

    @staticmethod
    def validate_coordinates(values):
        """Validate four integer coordinates in the range 0-800.

        Args:
            values: Sequence of four values.

        Returns:
            List of four validated integers.

        Raises:
            ValueError: If the count, type, or range is invalid.
        """
        values = list(values)
        if len(values) != 4:
            raise ValueError("expected four coordinates: restaurant x y and customer x y")
        result = []
        for value in values:
            if isinstance(value, bool) or not isinstance(value, int):
                raise ValueError("coordinates must be integers")
            if not config.COORD_MIN <= value <= config.COORD_MAX:
                raise ValueError(
                    f"coordinate {value} is outside the range "
                    f"{config.COORD_MIN}-{config.COORD_MAX}"
                )
            result.append(value)
        return result

    def create_order(self, coords):
        """Create and register a new order from four coordinates.

        Args:
            coords: ``[restaurant_x, restaurant_y, customer_x, customer_y]``.

        Returns:
            The newly created Order.

        Raises:
            ValueError: If the coordinates are invalid.
        """
        rx, ry, cx, cy = self.validate_coordinates(coords)
        order = Order((rx, ry), (cx, cy))
        orders = globalvar.get_value("orders")
        if orders is None:
            orders = []
            globalvar.set_value("orders", orders)
        orders.append(order)
        logger.info("Order %d created", order.id)
        return order

    def build_route(self, start, order):
        """Build the full route from a start point through the restaurant to the customer.

        Args:
            start: Starting ``(x, y)`` point.
            order: The order whose restaurant and customer define the route.

        Returns:
            List of lattice points forming a connected route.
        """
        to_restaurant = PathPlanner.plan(start, order.res_pos)
        to_customer = PathPlanner.plan(order.res_pos, order.cus_pos)
        return to_restaurant + to_customer[1:]

    def assign_order(self, order):
        """Assign an order to the best rider, recruiting one if necessary.

        Args:
            order: The Order to assign.

        Returns:
            Tuple ``(rider, new_rider_added, route)``.

        Raises:
            NoRiderAvailableError: If no rider can serve the order.
        """
        new_rider_added = self.system.ensure_capacity()
        rider = find_best_rider_for_order(order)
        order.assign_to(rider.rider_id)
        rider.orders.append(order)
        route = self.build_route(rider.position, order)
        logger.info("Order %d assigned to rider %d", order.id, rider.rider_id)
        return rider, new_rider_added, route

    def queue(self, order):
        """Hold an order until a rider becomes available.

        Args:
            order: The Order to queue.
        """
        if order not in self.pending:
            self.pending.append(order)

    def dispatch_pending(self):
        """Try to assign queued orders in arrival order.

        Returns:
            List of orders that were assigned during this call.
        """
        assigned = []
        for order in list(self.pending):
            try:
                self.assign_order(order)
            except NoRiderAvailableError:
                break
            self.pending.remove(order)
            assigned.append(order)
        return assigned

    @staticmethod
    def active_orders():
        """Return all orders that are not yet completed.

        Returns:
            List of Order objects.
        """
        orders = globalvar.get_value("orders") or []
        return [order for order in orders if order.status != Order.STATUS_COMPLETED]
