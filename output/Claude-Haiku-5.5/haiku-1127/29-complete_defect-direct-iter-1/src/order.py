"""Order assignment: rider selection and order management."""

import logging

import config
import globalvar
import grid
from order_model import Order

logger = logging.getLogger(__name__)


def find_best_rider_for_order(order):
    """Find the best available rider for an order.

    Strategy: distance-first. Among riders that still have capacity
    (fewer than ``MAX_ORDERS_PER_RIDER`` orders), the rider closest to the
    restaurant is preferred. A load penalty per already-assigned order
    balances work between riders (competitive, load-aware assignment).
    Ties are broken by the lower rider ID.

    Args:
        order: The Order to be assigned.

    Returns:
        Rider: The selected rider, or None if no rider has spare capacity.
    """
    riders = globalvar.get_value("riders", []) or []
    best = None
    best_key = None
    for rider in riders:
        if len(rider.orders) >= config.MAX_ORDERS_PER_RIDER:
            continue
        distance = grid.manhattan(rider.position, order.res_grid)
        key = (distance + config.LOAD_PENALTY * len(rider.orders), rider.rider_id)
        if best_key is None or key < best_key:
            best = rider
            best_key = key
    return best


class OrderManager:
    """Creates, assigns and tracks delivery orders."""

    def create_order(self, coords):
        """Create an order from four integer coordinates and store it.

        Args:
            coords: Sequence [restaurant_x, restaurant_y, customer_x, customer_y].

        Returns:
            Order: The newly created order.

        Raises:
            ValueError: If the sequence length or any coordinate is invalid.
        """
        if len(coords) != 4:
            raise ValueError("An order needs exactly four coordinates.")
        for value in coords:
            if not grid.is_valid_coordinate(value):
                raise ValueError(
                    f"Coordinate {value} is invalid; use integers in 0-800.")
        order = Order((coords[0], coords[1]), (coords[2], coords[3]))
        globalvar.get_value("orders").append(order)
        logger.info("Created order %s", order.id)
        return order

    def try_assign(self, order):
        """Assign an order to the best available rider.

        Args:
            order: The Order to assign.

        Returns:
            Rider or None: The rider that received the order, or None if no
            rider is available. The order is appended to ``rider.orders``.
        """
        rider = find_best_rider_for_order(order)
        if rider is None:
            return None
        order.assign_to(rider.rider_id)
        rider.orders.append(order)
        logger.info("Assigned order %s to rider %s", order.id, rider.rider_id)
        return rider

    def enqueue(self, order):
        """Keep an unassignable order in the pending queue for later retry.

        Args:
            order: The Order that could not be assigned.
        """
        pending = globalvar.get_value("pending_orders")
        if pending is not None and order not in pending:
            pending.append(order)

    def retry_pending(self):
        """Try to assign all pending orders.

        Returns:
            list[Rider]: Riders that received previously pending orders.
        """
        pending = globalvar.get_value("pending_orders", []) or []
        assigned = []
        for order in list(pending):
            rider = self.try_assign(order)
            if rider is not None:
                pending.remove(order)
                assigned.append(rider)
        return assigned

    def pending_orders(self):
        """Return the list of orders waiting for a rider."""
        return list(globalvar.get_value("pending_orders", []) or [])

    def all_orders(self):
        """Return all orders created in this session."""
        return list(globalvar.get_value("orders", []) or [])
