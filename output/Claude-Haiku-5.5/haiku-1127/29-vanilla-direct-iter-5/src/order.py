"""Order management: validation, creation, and rider assignment."""

from __future__ import annotations

import logging
import math
from typing import Any, List, Optional, Sequence

import globalvar
from order_model import Order
from rider import Rider

logger = logging.getLogger(__name__)

MIN_COORDINATE = 0
MAX_COORDINATE = 800
COORDINATE_LABELS = ("restaurant x", "restaurant y", "customer x", "customer y")


def validate_coordinates(values: Sequence[Any]) -> List[int]:
    """Validate and normalise ``[restaurant_x, restaurant_y, customer_x, customer_y]``.

    Args:
        values: Four values that must be integers in the range 0-800.

    Returns:
        The four coordinates as ``int``.

    Raises:
        ValueError: If the count, type or range is invalid.
    """
    try:
        items = list(values)
    except TypeError as exc:
        raise ValueError("Expected four coordinates") from exc
    if len(items) != 4:
        raise ValueError(
            "Expected 4 coordinates [restaurant_x, restaurant_y, customer_x, "
            f"customer_y], got {len(items)}")

    result: List[int] = []
    for label, raw in zip(COORDINATE_LABELS, items):
        if isinstance(raw, bool):
            raise ValueError(f"{label} must be an integer, got {raw!r}")
        if isinstance(raw, float):
            if not raw.is_integer():
                raise ValueError(f"{label} must be an integer, got {raw}")
            raw = int(raw)
        elif isinstance(raw, str):
            try:
                raw = int(raw.strip())
            except ValueError as exc:
                raise ValueError(f"{label} must be an integer, got '{raw}'") from exc
        elif not isinstance(raw, int):
            raise ValueError(f"{label} must be an integer, got {raw!r}")
        if not MIN_COORDINATE <= raw <= MAX_COORDINATE:
            raise ValueError(
                f"{label} {raw} is out of range {MIN_COORDINATE}-{MAX_COORDINATE}")
        result.append(raw)
    return result


def find_best_rider_for_order(order: Order) -> Optional[Rider]:
    """Return the rider closest to the order's restaurant.

    Distance is Euclidean: ``sqrt((rx - restaurant_x)^2 + (ry - restaurant_y)^2)``.
    Ties are broken by the smaller number of assigned orders (load balancing),
    then by rider ID.

    Args:
        order: The order needing a rider.

    Returns:
        The best rider, or None if no riders exist.
    """
    riders = globalvar.get_value("riders") or []
    best: Optional[Rider] = None
    best_key = None
    rest_x, rest_y = order.res_pos
    for rider in riders:
        distance = math.hypot(rider.x - rest_x, rider.y - rest_y)
        key = (round(distance, 6), len(rider.orders), rider.rider_id)
        if best_key is None or key < best_key:
            best = rider
            best_key = key
    return best


def assign_order(order: Order) -> Optional[Rider]:
    """Assign a pending order to the best rider.

    Args:
        order: Order to assign.

    Returns:
        The rider that received the order, or None if no rider is available.
    """
    if order.status != "pending":
        return None
    rider = find_best_rider_for_order(order)
    if rider is None:
        logger.warning("No rider available for order #%d", order.id)
        return None
    order.assign_to(rider.rider_id)
    rider.orders.append(order)
    logger.info("Order #%d assigned to rider #%d", order.id, rider.rider_id)
    return rider


class OrderManager:
    """Facade for order creation, lookup and assignment."""

    @staticmethod
    def create_order(coordinates: Sequence[Any], start_tick: Optional[int] = None) -> Order:
        """Validate coordinates, create an order and register it.

        Args:
            coordinates: ``[restaurant_x, restaurant_y, customer_x, customer_y]``.
            start_tick: Creation tick; defaults to the current simulation tick.

        Returns:
            The new ``Order``.

        Raises:
            ValueError: If the coordinates are invalid.
        """
        rest_x, rest_y, cus_x, cus_y = validate_coordinates(coordinates)
        if start_tick is None:
            start_tick = int(globalvar.get_value("current_tick", 0))
        order = Order((rest_x, rest_y), (cus_x, cus_y), start_tick)
        globalvar.get_value("orders").append(order)
        logger.info("Order #%d created: restaurant=%s customer=%s",
                    order.id, order.res_pos, order.cus_pos)
        return order

    @staticmethod
    def all_orders() -> List[Order]:
        """Return every order ever created (history included)."""
        return list(globalvar.get_value("orders") or [])

    @staticmethod
    def pending_orders() -> List[Order]:
        """Return orders still waiting for a rider."""
        return [o for o in OrderManager.all_orders() if o.status == "pending"]

    @staticmethod
    def active_orders() -> List[Order]:
        """Return orders that are not yet completed."""
        return [o for o in OrderManager.all_orders() if o.status != "completed"]

    @staticmethod
    def assign(order: Order) -> Optional[Rider]:
        """Assign ``order`` using :func:`assign_order`."""
        return assign_order(order)
