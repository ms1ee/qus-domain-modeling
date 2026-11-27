"""Order management: assignment, pending queue, completion and settlement."""

import logging

import globalvar
import grid
from order_model import Order, COMPLETED

logger = logging.getLogger("dispatch.order")

# Distance-equivalent penalty per already-queued order, used to balance load
# among riders that are roughly equally close.
LOAD_PENALTY = 50


def find_best_rider_for_order(order):
    """Find the best rider for an order using a distance-first strategy.

    The closest rider (Manhattan distance from its current position to the
    restaurant) wins. Each order already queued on a rider adds a load
    penalty so that work is spread across riders. Ties are broken by the
    lower rider id.

    Args:
        order: The order needing a rider.

    Returns:
        Rider: The selected rider, or None if no riders exist.
    """
    riders = globalvar.get_value("riders") or []
    best = None
    best_key = None
    for rider in riders:
        distance = grid.manhattan(rider.position, order.res_grid)
        key = (distance + LOAD_PENALTY * len(rider.orders), rider.rider_id)
        if best_key is None or key < best_key:
            best = rider
            best_key = key
    return best


class OrderManager:
    """Create, assign and settle orders.

    Attributes:
        pending: Orders waiting for a rider to become available.
        active: Orders assigned but not yet settled.
        history: Orders whose completion has been settled.
    """

    def __init__(self):
        """Initialise empty order queues."""
        self.pending = []
        self.active = []
        self.history = []

    def create_order(self, res_pos, cus_pos):
        """Create an order and register it in global storage.

        Args:
            res_pos: Restaurant ``(x, y)`` in 0-800.
            cus_pos: Customer ``(x, y)`` in 0-800.

        Returns:
            Order: The newly created order.
        """
        order = Order(res_pos, cus_pos)
        orders = globalvar.get_value("orders")
        if orders is None:
            orders = []
            globalvar.set_value("orders", orders)
        orders.append(order)
        logger.info("Order #%d created: restaurant %s customer %s",
                    order.id, order.restaurant_pos, order.customer_pos)
        return order

    def get_all_orders(self):
        """Return every order ever created."""
        return globalvar.get_value("orders") or []

    def assign(self, order):
        """Assign an order to the best rider, or queue it if none exists.

        Args:
            order: The order to assign.

        Returns:
            Rider: The rider that received the order, or None if the order
            was placed in the pending queue.
        """
        rider = find_best_rider_for_order(order)
        if rider is None:
            if order not in self.pending:
                self.pending.append(order)
            logger.warning("No rider available for order #%d", order.id)
            return None
        if order in self.pending:
            self.pending.remove(order)
        order.assign_to(rider.rider_id)
        rider.orders.append(order)
        if order not in self.active:
            self.active.append(order)
        logger.info("Order #%d assigned to rider #%d",
                    order.id, rider.rider_id)
        return rider

    def dispatch_pending(self):
        """Try to assign every pending order.

        Returns:
            list[tuple[Order, Rider]]: Orders that were newly assigned.
        """
        assigned = []
        for order in list(self.pending):
            rider = self.assign(order)
            if rider is not None:
                assigned.append((order, rider))
        return assigned

    def settle_completed(self):
        """Book revenue for completed orders and release their resources.

        Revenue is ``order_revenue`` minus a fuel cost of
        ``fuel_cost_per_100_units`` for every 100 units travelled. Funds may
        become negative.

        Returns:
            list[Order]: Orders settled during this call.
        """
        config = globalvar.get_value("config") or {}
        revenue = int(config.get("order_revenue", 150))
        fuel_rate = int(config.get("fuel_cost_per_100_units", 2))
        settled = []
        for order in list(self.active):
            if order.status != COMPLETED or order.settled:
                continue
            fuel_cost = (order.distance // 100) * fuel_rate
            net = revenue - fuel_cost
            globalvar.set_value("funds",
                                (globalvar.get_value("funds") or 0) + net)
            order.settled = True
            self.active.remove(order)
            self.history.append(order)
            settled.append(order)
            logger.info("Order #%d settled, net %d", order.id, net)
        return settled
