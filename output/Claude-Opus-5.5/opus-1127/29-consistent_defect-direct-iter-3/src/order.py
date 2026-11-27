"""Order creation, coordinate conversion and assignment."""

import logging
import math

import globalvar
import system
from order_model import Order

logger = logging.getLogger(__name__)

MAP_SIZE = 800
CELL_SIZE = 100


def convert_coordinate(value):
    """Convert an input coordinate to the top-left corner of its grid cell."""
    value = max(0, min(MAP_SIZE, int(value)))
    return (value // CELL_SIZE) * CELL_SIZE


def grid_center(value):
    """Return the centre of the grid cell containing ``value``."""
    value = max(0, min(MAP_SIZE - 1, int(value)))
    return (value // CELL_SIZE) * CELL_SIZE + CELL_SIZE // 2


def convert_order_input(coords):
    """Convert ``[rx, ry, cx, cy]`` into restaurant/customer grid points."""
    if len(coords) != 4:
        raise ValueError("Exactly four coordinates are required")
    rx, ry, cx, cy = (convert_coordinate(c) for c in coords)
    return (rx, ry), (cx, cy)


def _distance(rider, pos):
    return math.sqrt((rider.x - int(pos[0])) ** 2 + (rider.y - int(pos[1])) ** 2)


def find_best_rider_for_order(order):
    """Return the best rider for ``order``.

    Riders with the fewest current (uncompleted) orders are preferred; among
    those the closest rider to the restaurant (Euclidean distance) wins, and
    ties are broken by rider id.  If no rider exists one is recruited when
    funds permit; otherwise None is returned.
    """
    riders = globalvar.get_value("riders") or []
    if not riders:
        return system.recruit_rider()
    return min(riders, key=lambda r: (r.active_order_count(),
                                      _distance(r, order.res_pos),
                                      r.rider_id))


class OrderManager:
    """Handles order creation, assignment and queries."""

    @staticmethod
    def all_orders():
        orders = globalvar.get_value("orders")
        if orders is None:
            orders = []
            globalvar.set_value("orders", orders)
        return orders

    @staticmethod
    def create_order(coords):
        """Create and assign an order.

        Returns ``(order, rider, new_rider_added)``.
        """
        res_pos, cus_pos = convert_order_input(coords)
        order = Order(res_pos, cus_pos)
        OrderManager.all_orders().append(order)
        before = len(globalvar.get_value("riders") or [])
        system.auto_recruit()
        rider = find_best_rider_for_order(order)
        after = len(globalvar.get_value("riders") or [])
        if rider is not None:
            OrderManager.assign(order, rider)
        else:
            logger.warning("No rider available for order %s", order.id)
        return order, rider, after > before

    @staticmethod
    def assign(order, rider):
        """Assign ``order`` to ``rider``."""
        order.assign_to(rider.rider_id)
        rider.orders.append(order)

    @staticmethod
    def assign_pending():
        """Try to assign orders that previously had no rider."""
        for order in OrderManager.all_orders():
            if order.status == "pending":
                rider = find_best_rider_for_order(order)
                if rider is not None:
                    OrderManager.assign(order, rider)

    @staticmethod
    def get_order(order_id):
        for order in OrderManager.all_orders():
            if order.id == order_id:
                return order
        return None
