"""Order management: input validation, creation, rider assignment and history."""

import logging
from typing import Any, List, Optional, Sequence, Tuple

import globalvar
from order_model import STATUS_ASSIGNED, Order
from path_planner import MAP_SIZE, PathPlanner
from rider import STATE_IDLE, Rider

logger = logging.getLogger(__name__)

DEFAULT_LOAD_PENALTY = 100


def validate_coordinates(values: Sequence[Any]) -> List[int]:
    """Validate ``[restaurant_x, restaurant_y, customer_x, customer_y]``.

    Args:
        values: Four integers (or strings representing integers).

    Returns:
        The four values converted to ``int``.

    Raises:
        ValueError: If the count is wrong, a value is not an integer, or a
            value lies outside the range 0-800.
    """
    if len(values) != 4:
        raise ValueError(f"expected 4 coordinates, got {len(values)}")
    result: List[int] = []
    for raw in values:
        if isinstance(raw, bool):
            raise ValueError(f"'{raw}' is not a valid integer coordinate")
        try:
            number = raw if isinstance(raw, int) else int(str(raw).strip())
        except ValueError:
            raise ValueError(f"'{raw}' is not an integer") from None
        if not 0 <= number <= MAP_SIZE:
            raise ValueError(f"coordinate {number} is out of range 0-{MAP_SIZE}")
        result.append(number)
    return result


def find_best_rider_for_order(order: Order) -> Optional[Rider]:
    """Select the most suitable rider for ``order``.

    Candidates are idle riders with no queued orders when any exist; otherwise
    all riders are candidates. The cost is the Manhattan distance from the
    rider to the restaurant plus a load penalty for every queued order, so
    distance is the primary criterion and load balancing the secondary one.

    Args:
        order: The order to be assigned.

    Returns:
        The chosen :class:`Rider`, or None if the system has no riders at all
        (the caller is then expected to recruit one).
    """
    riders = globalvar.get_value("riders", []) or []
    if not riders:
        return None

    params = globalvar.get_value("params", {}) or {}
    penalty = int(params.get("load_penalty", DEFAULT_LOAD_PENALTY))

    idle = [r for r in riders if r.state == STATE_IDLE and not r.orders]
    candidates = idle if idle else list(riders)

    best: Optional[Rider] = None
    best_key: Optional[Tuple[int, int]] = None
    for rider in candidates:
        distance = PathPlanner.manhattan(rider.position, order.res_pos)
        cost = distance + penalty * len(rider.orders)
        key = (cost, rider.rider_id)
        if best_key is None or key < best_key:
            best, best_key = rider, key
    return best


class OrderManager:
    """Creates, assigns and tracks delivery orders."""

    def _order_list(self) -> List[Order]:
        """Return the global order history list, creating it if needed."""
        orders = globalvar.get_value("orders")
        if orders is None:
            orders = []
            globalvar.set_value("orders", orders)
        return orders

    def create_order(self, coords: Sequence[Any]) -> Order:
        """Validate coordinates and create a new order.

        Args:
            coords: ``[restaurant_x, restaurant_y, customer_x, customer_y]``.

        Returns:
            The newly created :class:`Order`, stored in the order history.

        Raises:
            ValueError: If the coordinates are invalid.
        """
        values = validate_coordinates(coords)
        order = Order(values[0:2], values[2:4])
        self._order_list().append(order)
        logger.info("Order %d created", order.id)
        return order

    def assign_order(self, order: Order, system: Any) -> Tuple[Optional[Rider], bool]:
        """Assign ``order`` to the best rider, recruiting one if necessary.

        Args:
            order: The order to assign.
            system: The :class:`system.SystemManager` used for recruitment.

        Returns:
            ``(rider, is_new)``: the assigned rider (None if assignment failed)
            and whether a new rider was recruited for this order.
        """
        is_new = False
        riders = globalvar.get_value("riders", []) or []
        idle = [r for r in riders if r.state == STATE_IDLE and not r.orders]
        if not idle:
            if system.recruit_rider() is not None:
                is_new = True

        rider = find_best_rider_for_order(order)
        if rider is None:
            order.cancel()
            return None, False

        order.assign_to(rider.rider_id)
        rider.orders.append(order)
        logger.info("Order %d assigned to rider %d (new=%s)", order.id, rider.rider_id, is_new)
        return rider, is_new

    def history(self) -> List[Order]:
        """Return every order created so far."""
        return list(self._order_list())

    def active_orders(self) -> List[Order]:
        """Return orders that are assigned and not yet delivered."""
        return [o for o in self._order_list() if o.status == STATUS_ASSIGNED]
