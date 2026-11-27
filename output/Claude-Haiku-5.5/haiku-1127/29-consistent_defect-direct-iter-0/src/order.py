"""Order management: creation, distance-first assignment and dispatch."""

import logging

import globalvar
from order_model import Order, STATUS_PENDING
from path_planner import PathPlanner

logger = logging.getLogger(__name__)

MIN_COORD = 0
MAX_COORD = 1000


def find_best_rider_for_order(order):
    """Choose the best rider for an order.

    The rider with the fewest active orders is preferred. Ties are broken by
    the Euclidean distance from the rider to the restaurant.

    Args:
        order: Order whose restaurant location drives the distance check.

    Returns:
        Rider | None: Selected rider, or None when no riders exist.
    """
    riders = globalvar.get_value("riders", []) or []
    if not riders:
        return None

    def sort_key(rider):
        return (
            rider.active_order_count(),
            PathPlanner.euclidean(rider.position, order.res_pos),
        )

    return min(riders, key=sort_key)


class OrderManager:
    """Creates, dispatches and tracks orders.

    Attributes:
        system: SystemManager used for rider recruitment.
        pending (list[Order]): Orders waiting for a rider.
    """

    def __init__(self, system):
        """Create an order manager bound to a system manager.

        Args:
            system: SystemManager instance.
        """
        self.system = system
        self.pending = []

    @staticmethod
    def validate_coordinates(coords):
        """Validate a four-element coordinate list.

        Args:
            coords: Sequence ``[restaurant_x, restaurant_y, customer_x, customer_y]``.

        Returns:
            list[int]: Validated integers.

        Raises:
            ValueError: If the format or range is invalid.
        """
        if len(coords) != 4:
            raise ValueError("Exactly 4 coordinates are required.")
        values = []
        for value in coords:
            if isinstance(value, bool) or not isinstance(value, int):
                raise ValueError("Coordinates must be integers.")
            if not MIN_COORD <= value <= MAX_COORD:
                raise ValueError(
                    "Coordinates must be within %d-%d." % (MIN_COORD, MAX_COORD)
                )
            values.append(value)
        return values

    def create_order(self, coords):
        """Create an order from raw coordinates and register it globally.

        Args:
            coords: ``[restaurant_x, restaurant_y, customer_x, customer_y]``.

        Returns:
            Order: The newly created order (status "pending").

        Raises:
            ValueError: If the coordinates are invalid.
        """
        rx, ry, cx, cy = self.validate_coordinates(list(coords))
        order = Order((rx, ry), (cx, cy))
        globalvar.get_value("orders").append(order)
        logger.info("Created order %s", order.id)
        return order

    def dispatch(self, order):
        """Queue an order, recruit if needed, and assign it to a rider.

        Args:
            order: Order to dispatch.

        Returns:
            tuple[Rider | None, bool]: (assigned rider or None, whether a new
            rider was recruited during this dispatch).
        """
        if order not in self.pending:
            self.pending.append(order)
        recruited = self.system.try_recruit(len(self.pending)) is not None
        rider = self._assign(order)
        return rider, recruited

    def retry_pending(self):
        """Attempt to assign all pending orders (called each tick).

        Returns:
            list[Order]: Orders assigned during this call.
        """
        assigned = []
        for order in list(self.pending):
            self.system.try_recruit(len(self.pending))
            if self._assign(order) is not None:
                assigned.append(order)
        return assigned

    def _assign(self, order):
        """Assign an order to the best rider if one exists.

        Args:
            order: Order to assign.

        Returns:
            Rider | None: The rider that received the order.
        """
        rider = find_best_rider_for_order(order)
        if rider is None:
            return None
        order.assign_to(rider.rider_id)
        rider.orders.append(order)
        if order in self.pending:
            self.pending.remove(order)
        logger.info("Order %s assigned to rider %s", order.id, rider.rider_id)
        return rider

    @staticmethod
    def all_orders():
        """All orders created in this session.

        Returns:
            list[Order]: Order list from the global store.
        """
        return globalvar.get_value("orders", [])

    def completed_orders(self):
        """Orders whose delivery has finished.

        Returns:
            list[Order]: Completed orders.
        """
        return [o for o in self.all_orders() if o.status == "completed"]

    def unassigned_count(self):
        """Number of orders still waiting for a rider.

        Returns:
            int: Count of pending orders.
        """
        return sum(1 for o in self.pending if o.status == STATUS_PENDING)
