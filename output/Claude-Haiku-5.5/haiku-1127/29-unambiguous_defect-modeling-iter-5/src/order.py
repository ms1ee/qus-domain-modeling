"""Order management: creation, rider assignment and completion tracking."""

import globalvar
from order_model import Order, STATUS_COMPLETED
from path_planner import manhattan
from rider import Rider  # noqa: F401  (imported for type reference)

MAX_ORDERS_PER_RIDER = 3
LOAD_PENALTY = 150


def find_best_rider_for_order(order):
    """Select the most suitable rider for an order.

    The score of a rider is the Manhattan distance from its current position
    to the restaurant plus a penalty per already-assigned order, which balances
    load between riders. The lowest score wins; ties go to the lower rider ID.

    Args:
        order: The :class:`Order` to assign.

    Returns:
        The chosen :class:`Rider`, or ``None`` if no rider has spare capacity.
    """
    riders = globalvar.get_value("riders") or []
    best = None
    best_score = None
    for rider in riders:
        if len(rider.orders) >= MAX_ORDERS_PER_RIDER:
            continue
        distance = manhattan(rider.position, order.restaurant_pos)
        score = distance + LOAD_PENALTY * len(rider.orders)
        if (best is None or score < best_score
                or (score == best_score and rider.rider_id < best.rider_id)):
            best = rider
            best_score = score
    return best


class OrderManager:
    """Creates, assigns and tracks orders.

    Attributes:
        order_counter (int): Number of orders created so far.
        orders (list[Order]): All orders in creation order.
    """

    def __init__(self):
        """Create an empty order manager."""
        self.order_counter = 0
        self.orders = []

    def create_order(self, restaurant_pos, customer_pos, start_time=0):
        """Create and register a new order.

        Args:
            restaurant_pos: Restaurant point ``[x, y]``.
            customer_pos: Customer point ``[x, y]``.
            start_time: Simulated creation time.

        Returns:
            The newly created :class:`Order`.
        """
        order = Order(restaurant_pos, customer_pos, start_time)
        self.orders.append(order)
        self.order_counter += 1
        return order

    @staticmethod
    def assign_order(order, rider):
        """Assign an order to a rider by appending it to ``rider.orders``.

        Args:
            order: The order to assign.
            rider: The receiving rider.
        """
        order.assign_to(rider.rider_id)
        rider.orders.append(order)

    def assign_best(self, order):
        """Find the best rider for ``order`` and assign it.

        Args:
            order: The order to assign.

        Returns:
            The rider that received the order, or ``None``.
        """
        rider = find_best_rider_for_order(order)
        if rider is not None:
            self.assign_order(order, rider)
        return rider

    @staticmethod
    def complete_order(order, time):
        """Mark an order as completed at ``time``.

        Args:
            order: The completed order.
            time: Simulated completion time.
        """
        order.complete(time)

    def completed_orders(self):
        """Return the list of completed orders."""
        return [o for o in self.orders if o.status == STATUS_COMPLETED]

    def find_order(self, order_id):
        """Return the order with ``order_id`` or ``None``."""
        for order in self.orders:
            if order.id == order_id:
                return order
        return None
