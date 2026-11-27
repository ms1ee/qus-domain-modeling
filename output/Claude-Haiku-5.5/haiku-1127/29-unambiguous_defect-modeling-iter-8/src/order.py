"""Order management and distance-first rider assignment."""

from typing import List, Optional

import globalvar
from grid_map import manhattan
from order_model import Order
from rider import Rider

LOAD_PENALTY = 150


def find_best_rider_for_order(order: Order) -> Rider:
    """Select the best rider for an order.

    The score is the Manhattan distance from the rider to the restaurant plus
    a load penalty per active order, so nearby and lightly loaded riders are
    preferred. Riders already at their order limit are skipped.

    Args:
        order: The order that needs a rider.

    Returns:
        The selected Rider, or None if no rider can take the order.
    """
    riders = globalvar.get_value("riders") or []
    max_orders = globalvar.get_value("max_orders_per_rider") or 3
    best = None
    best_key = None
    for rider in riders:
        load = len(rider.orders)
        if load >= max_orders:
            continue
        distance = manhattan((rider.x, rider.y), order.res_pos)
        key = (distance + load * LOAD_PENALTY, rider.rider_id)
        if best_key is None or key < best_key:
            best = rider
            best_key = key
    return best


class OrderManager:
    """Creates, assigns and tracks orders."""

    @property
    def orders(self) -> List[Order]:
        """Return the list of all orders stored in the global store.

        Returns:
            List of Order objects.
        """
        orders = globalvar.get_value("orders")
        if orders is None:
            orders = []
            globalvar.set_value("orders", orders)
        return orders

    def create_order(self, res_pos, cus_pos) -> Order:
        """Create an order and register it.

        Args:
            res_pos: Restaurant position (x, y).
            cus_pos: Customer position (x, y).

        Returns:
            The newly created Order.
        """
        order = Order(res_pos, cus_pos)
        self.orders.append(order)
        return order

    def assign(self, order: Order) -> Optional[Rider]:
        """Assign an order to the best available rider.

        Args:
            order: Order to assign.

        Returns:
            The rider that received the order, or None if none is available.
        """
        rider = find_best_rider_for_order(order)
        if rider is None:
            return None
        rider.orders.append(order)
        order.assign_to(rider.rider_id)
        return rider

    def discard(self, order: Order) -> None:
        """Mark an order as rejected and remove it from the registry.

        Args:
            order: Order to discard.
        """
        order.status = "rejected"
        if order in self.orders:
            self.orders.remove(order)

    def active_orders(self) -> List[Order]:
        """Return orders that are still in progress.

        Returns:
            Orders whose status is not completed or rejected.
        """
        return [o for o in self.orders if o.status not in ("completed", "rejected")]

    def completed_orders(self) -> List[Order]:
        """Return orders that have been delivered.

        Returns:
            Orders with status completed.
        """
        return [o for o in self.orders if o.status == "completed"]
