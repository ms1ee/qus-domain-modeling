"""Order assignment: distance-first rider selection with load balancing."""

import logging

import globalvar
from grid import manhattan
from order_model import Order

logger = logging.getLogger("dispatch.order")

MAX_ORDERS_PER_RIDER = 3
LOAD_PENALTY = 300


def find_best_rider_for_order(order):
    """Select the most suitable rider for an order.

    The score of a rider is its Manhattan distance to the restaurant plus a
    load penalty per already queued order. Ties are broken by rider id.
    Riders already holding ``MAX_ORDERS_PER_RIDER`` orders are skipped.

    Args:
        order: The Order that needs a rider.

    Returns:
        Rider: The best candidate, or None if no rider can take the order.
    """
    best = None
    best_key = None
    for rider in globalvar.get_value("riders") or []:
        if len(rider.orders) >= MAX_ORDERS_PER_RIDER:
            continue
        distance = manhattan((rider.x, rider.y), order.res_pos)
        key = (distance + LOAD_PENALTY * len(rider.orders), rider.rider_id)
        if best_key is None or key < best_key:
            best, best_key = rider, key
    return best


class OrderManager:
    """Creates, assigns and settles orders.

    Attributes:
        orders (list[Order]): History of every accepted order.
    """

    def __init__(self):
        """Create an empty order manager."""
        self.orders = []
        self._active = []

    def create_order(self, res_pos, cus_pos):
        """Create an order from raw coordinates without registering it.

        Args:
            res_pos: Restaurant input point (x, y).
            cus_pos: Customer input point (x, y).

        Returns:
            Order: The new, unassigned order.
        """
        return Order(res_pos, cus_pos)

    def assign_order(self, order):
        """Assign an order to the best rider and register it.

        Args:
            order: An Order created by ``create_order``.

        Returns:
            Rider | None: The rider that received the order, or None if no
            rider was available (the order is then not registered).
        """
        rider = find_best_rider_for_order(order)
        if rider is None:
            logger.info("no rider available for order %d", order.id)
            return None
        rider.orders.append(order)
        order.assign_to(rider.rider_id)
        self.orders.append(order)
        self._active.append(order)
        return rider

    def active_orders(self):
        """Return orders that are assigned but not yet completed."""
        return list(self._active)

    def settle_completed(self):
        """Remove and return orders completed since the last call.

        Returns:
            list[Order]: Newly completed orders.
        """
        done = [o for o in self._active if o.status == "completed"]
        if done:
            self._active = [o for o in self._active if o.status != "completed"]
        return done

    def find_order(self, order_id):
        """Return the order with ``order_id`` or None."""
        for order in self.orders:
            if order.id == order_id:
                return order
        return None
