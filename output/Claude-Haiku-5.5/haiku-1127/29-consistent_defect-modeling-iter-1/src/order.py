"""Order creation, coordinate transformation and rider assignment."""

import logging
import math
from typing import List, Optional, Sequence, Tuple

from globalvar import get_value
from order_model import Order
from rider import Rider

logger = logging.getLogger(__name__)

INPUT_MIN = 0
INPUT_MAX = 1000
MAP_MIN = 0
MAP_MAX = 800
CELL_SIZE = 100


def transform_coordinate(value: int) -> int:
    """Convert an input coordinate to the top-left corner of its grid cell.

    Values outside the map are clamped into 0..800 first.

    Args:
        value: Raw coordinate supplied by the user.

    Returns:
        ``(clamped // 100) * 100``.
    """
    clamped = min(max(int(value), MAP_MIN), MAP_MAX)
    return (clamped // CELL_SIZE) * CELL_SIZE


def build_order(values: Sequence[int], start_time: int = 0) -> Order:
    """Create an Order from ``[restaurant_x, restaurant_y, customer_x, customer_y]``.

    Args:
        values: Four integer coordinates.
        start_time: Simulated tick at creation.

    Returns:
        A new Order with grid-aligned restaurant and customer positions.

    Raises:
        ValueError: If the input is not four integers in the allowed range.
    """
    if len(values) != 4:
        raise ValueError("An order requires exactly four coordinates.")
    checked: List[int] = []
    for value in values:
        if isinstance(value, bool) or not isinstance(value, int):
            raise ValueError("Order coordinates must be integers.")
        if not INPUT_MIN <= value <= INPUT_MAX:
            raise ValueError(f"Coordinate {value} is outside {INPUT_MIN}-{INPUT_MAX}.")
        checked.append(value)
    res = (transform_coordinate(checked[0]), transform_coordinate(checked[1]))
    cus = (transform_coordinate(checked[2]), transform_coordinate(checked[3]))
    return Order(res, cus, start_time)


def find_best_rider_for_order(order: Order) -> Optional[Rider]:
    """Select the rider that should receive ``order``.

    Riders with the fewest active orders are considered first; among them the
    rider closest to the restaurant (Euclidean distance) is chosen, with the
    lowest rider id breaking ties.

    Args:
        order: The order needing a rider.

    Returns:
        The chosen Rider, or None if no rider exists.
    """
    riders: List[Rider] = get_value("riders") or []
    if not riders:
        return None
    fewest = min(len(r.active_orders()) for r in riders)
    candidates = [r for r in riders if len(r.active_orders()) == fewest]

    def key(r: Rider) -> Tuple[float, int]:
        dist = math.sqrt((r.x - order.res_pos[0]) ** 2 + (r.y - order.res_pos[1]) ** 2)
        return dist, r.rider_id

    return min(candidates, key=key)


def attach_order_to_rider(order: Order, rider: Rider) -> None:
    """Assign ``order`` to ``rider`` by appending it to the rider's list."""
    rider.orders.append(order)
    order.assign_to(rider.rider_id)
    logger.info("Order %s assigned to rider %s", order.id, rider.rider_id)


class OrderManager:
    """Creates, assigns and tracks orders in the global order list."""

    def create_order(self, values: Sequence[int], start_time: int = 0) -> Order:
        """Create an order and register it as pending."""
        order = build_order(values, start_time)
        orders: List[Order] = get_value("orders")
        orders.append(order)
        logger.info("Order %s created: %s -> %s", order.id, order.res_pos, order.cus_pos)
        return order

    def assign_order(self, order: Order) -> Optional[Rider]:
        """Assign a pending order to the best rider, if any exists."""
        rider = find_best_rider_for_order(order)
        if rider is not None:
            attach_order_to_rider(order, rider)
        return rider

    def orders(self) -> List[Order]:
        """Return all orders in creation order."""
        return list(get_value("orders") or [])

    def pending_orders(self) -> List[Order]:
        """Return orders that have not been assigned yet."""
        return [o for o in self.orders() if o.status == "pending"]

    def completed_orders(self) -> List[Order]:
        """Return delivered orders."""
        return [o for o in self.orders() if o.status == "completed"]
