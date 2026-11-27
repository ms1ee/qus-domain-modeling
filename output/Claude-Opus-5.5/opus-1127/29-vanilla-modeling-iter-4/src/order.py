"""Order management: creation, assignment and completion tracking."""

import logging
import math

import globalvar
from order_model import Order, OrderStatus

logger = logging.getLogger(__name__)


def rider_distance(rider, order):
    """Euclidean distance between a rider and the order's restaurant."""
    rx, ry = order.res_pos
    return math.sqrt((rider.x - rx) ** 2 + (rider.y - ry) ** 2)


def find_best_rider_for_order(order, riders=None):
    """Return the best rider for ``order`` (closest rider first).

    Idle riders are preferred; if none is idle, the least loaded / closest
    rider is chosen. Returns None when no rider exists.
    """
    if riders is None:
        riders = globalvar.get_value("riders") or []
    if not riders:
        return None
    idle = [r for r in riders if r.state == 0 and not r.orders]
    if idle:
        return min(idle, key=lambda r: (rider_distance(r, order), r.rider_id))
    return min(riders, key=lambda r: (len(r.orders), rider_distance(r, order), r.rider_id))


class OrderManager:
    """Handles order creation, assignment and completion."""

    def __init__(self, system=None):
        self.system = system

    @staticmethod
    def all_orders():
        """Return the global order history list."""
        orders = globalvar.get_value("orders")
        if orders is None:
            orders = []
            globalvar.set_value("orders", orders)
        return orders

    def create_order(self, coords):
        """Create an order from ``[res_x, res_y, cus_x, cus_y]``."""
        if len(coords) != 4:
            raise ValueError("An order requires exactly 4 coordinates")
        order = Order((coords[0], coords[1]), (coords[2], coords[3]))
        self.all_orders().append(order)
        logger.info("Created order %s", order)
        return order

    def pending_orders(self):
        """Orders not yet assigned to any rider."""
        return [o for o in self.all_orders() if o.status == OrderStatus.PENDING]

    def assign(self, order, rider):
        """Assign ``order`` to ``rider``."""
        rider.orders.append(order)
        order.assign_to(rider.rider_id)
        logger.info("Order %s assigned to rider %s", order.id, rider.rider_id)

    def dispatch(self, order):
        """Recruit riders if needed and assign ``order`` to the best rider.

        Returns:
            tuple(Rider | None, list[Rider]): assigned rider and newly
            recruited riders.
        """
        recruited = []
        if self.system is not None:
            recruited = self.system.check_recruitment()
        rider = find_best_rider_for_order(order)
        if rider is not None:
            self.assign(order, rider)
        return rider, recruited

    def create_and_dispatch(self, coords):
        """Create and dispatch an order in one step."""
        order = self.create_order(coords)
        rider, recruited = self.dispatch(order)
        return order, rider, recruited

    def dispatch_pending(self):
        """Try to assign every pending order."""
        results = []
        for order in self.pending_orders():
            rider, recruited = self.dispatch(order)
            results.append((order, rider, recruited))
        return results

    def completed_orders(self):
        """Return completed orders."""
        return [o for o in self.all_orders() if o.status == OrderStatus.COMPLETED]
