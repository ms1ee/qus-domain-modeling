"""Order assignment: distance-first rider selection with load balancing.

Also provides OrderManager, which creates orders, assigns them and tracks
the global order list.
"""

import logging

import config
import globalvar
import grid_map
from order_model import Order
from rider import Rider
from system import SystemManager

logger = logging.getLogger(__name__)


def _orders_list():
    """Return the global order list, creating it if missing."""
    orders = globalvar.get_value("orders")
    if orders is None:
        orders = []
        globalvar.set_value("orders", orders)
    return orders


def _score(rider, order):
    """Score a rider for an order; lower is better.

    The score is the Manhattan distance from the rider to the restaurant plus
    a penalty per already-assigned order (load balancing).
    """
    distance = grid_map.manhattan(rider.position, order.res_pos)
    return distance + config.SETTINGS["load_penalty"] * len(rider.orders)


def find_best_rider_for_order(order) -> Rider:
    """Select the best rider for an order, recruiting one if needed.

    A new rider is recruited when there are no riders, or when every rider
    has already reached the order load limit and recruitment is affordable.

    Args:
        order: The Order to be assigned.

    Returns:
        The selected Rider. The caller appends the order to rider.orders.

    Raises:
        RuntimeError: If there is no rider and none can be recruited.
    """
    manager = SystemManager()
    limit = config.SETTINGS["order_load_limit"]
    riders = list(globalvar.get_value("riders") or [])
    if not riders or all(len(r.orders) >= limit for r in riders):
        recruited = manager.recruit_rider()
        if recruited is not None:
            logger.info("Recruited rider %s for order %s", recruited.rider_id, order.order_id)
        riders = list(globalvar.get_value("riders") or [])
    if not riders:
        raise RuntimeError(
            "No rider available and recruitment is not possible "
            "(insufficient funds or capacity)."
        )
    return min(riders, key=lambda rider: _score(rider, order))


class OrderManager:
    """Creates, assigns and tracks orders."""

    def __init__(self, system=None):
        """Create an order manager.

        Args:
            system: Optional SystemManager; a new facade is used if omitted.
        """
        self.system = system if system is not None else SystemManager()

    def create_order(self, restaurant, customer) -> Order:
        """Create an order from raw restaurant and customer coordinates.

        Args:
            restaurant: (x, y) restaurant coordinates.
            customer: (x, y) customer coordinates.

        Returns:
            The newly created Order (coordinates already snapped to the grid).
        """
        order = Order(restaurant, customer)
        _orders_list().append(order)
        logger.info("Created order %s", order.order_id)
        return order

    def assign_order(self, order):
        """Assign an order to the best rider.

        Args:
            order: Order to assign.

        Returns:
            Tuple (rider, new_rider_added).

        Raises:
            RuntimeError: If no rider can serve the order. The order is
                removed from the order list in that case.
        """
        riders_before = len(self.system.riders)
        try:
            rider = find_best_rider_for_order(order)
        except RuntimeError:
            self.cancel_order(order)
            raise
        order.assign_to(rider.rider_id)
        rider.orders.append(order)
        new_rider = len(self.system.riders) > riders_before
        logger.info("Order %s assigned to rider %s", order.order_id, rider.rider_id)
        return rider, new_rider

    def cancel_order(self, order):
        """Remove an order from the global order list.

        Args:
            order: Order to remove.
        """
        orders = _orders_list()
        if order in orders:
            orders.remove(order)

    def all_orders(self):
        """Return a copy of all orders, including completed ones."""
        return list(_orders_list())

    def active_orders(self):
        """Return orders that are not yet completed."""
        return [o for o in _orders_list() if o.status != "completed"]
