"""Order assignment and order lifecycle management."""

import logging

import globalvar
from order_model import Order

logger = logging.getLogger("dispatch.order")

DEFAULT_MAX_ORDERS = 2


def _max_orders_per_rider():
    """Return the configured maximum queue length per rider."""
    config = globalvar.get_value("config") or {}
    return int(config.get("max_orders_per_rider", DEFAULT_MAX_ORDERS))


def find_best_rider_for_order(order):
    """Select the most suitable rider for ``order``.

    Strategy (distance-first with load balancing):
        * Only riders whose order queue is not full are candidates.
        * The rider with the smallest Manhattan distance to the restaurant
          wins; ties are broken by the shorter order queue, then by rider id.

    Args:
        order: The ``Order`` to be assigned.

    Returns:
        The chosen ``Rider``, or ``None`` if no rider can take the order.
    """
    limit = _max_orders_per_rider()
    rx, ry = order.restaurant_pos
    best = None
    best_key = None
    for rider in globalvar.get_value("riders", []):
        if len(rider.orders) >= limit:
            continue
        distance = abs(rider.x - rx) + abs(rider.y - ry)
        key = (distance, len(rider.orders), rider.rider_id)
        if best_key is None or key < best_key:
            best = rider
            best_key = key
    return best


class OrderManager:
    """Creates, assigns, cancels, and tracks orders."""

    def create_order(self, coords):
        """Create and register an order from four integer coordinates.

        Args:
            coords: Sequence ``[restaurant_x, restaurant_y, customer_x, customer_y]``.

        Returns:
            The newly created ``Order``.

        Raises:
            ValueError: If the sequence length is wrong or a coordinate is
                outside 0-800.
        """
        if len(coords) != 4:
            raise ValueError("An order needs exactly four coordinates.")
        order = Order((coords[0], coords[1]), (coords[2], coords[3]))
        orders = globalvar.get_value("orders")
        if orders is None:
            orders = []
            globalvar.set_value("orders", orders)
        orders.append(order)
        logger.info("Order %s created: %s -> %s", order.id, order.restaurant_pos, order.customer_pos)
        return order

    def assign(self, order, rider):
        """Append ``order`` to ``rider``'s queue and mark it assigned."""
        rider.orders.append(order)
        order.assign_to(rider.rider_id)
        logger.info("Order %s assigned to rider %s", order.id, rider.rider_id)
        return rider

    def dispatch(self, order):
        """Find the best rider for ``order`` and assign it.

        Returns:
            The assigned ``Rider``, or ``None`` if no rider is available.
        """
        rider = find_best_rider_for_order(order)
        if rider is None:
            return None
        return self.assign(order, rider)

    def cancel(self, order):
        """Remove a rejected order from the order registry."""
        orders = globalvar.get_value("orders", [])
        if order in orders:
            orders.remove(order)
        logger.info("Order %s cancelled", order.id)

    def active_orders(self):
        """Return orders that have not been completed yet."""
        return [o for o in globalvar.get_value("orders", []) if o.status != "completed"]

    def completed_orders(self):
        """Return orders that have been delivered."""
        return [o for o in globalvar.get_value("orders", []) if o.status == "completed"]
