"""Order creation, rider assignment and order flow orchestration."""

import logging
import math
from typing import Any, Dict, List, Optional

import globalvar
from order_model import ORDER_PENDING, Order
from path_planner import MAP_SIZE, PathPlanner
from rider import Rider

logger = logging.getLogger(__name__)

COORD_MIN = 0
COORD_MAX = 1000


def find_best_rider_for_order(order: Order) -> Optional[Rider]:
    """Select the best rider for an order.

    The rider with the fewest active orders is preferred. Ties are broken by
    the Euclidean distance from the rider to the restaurant, then by rider ID.

    Args:
        order: The order needing a rider.

    Returns:
        The chosen Rider, or None if no riders exist.
    """
    riders = globalvar.get_value("riders") or []
    best: Optional[Rider] = None
    best_key = None
    for rider in riders:
        key = (
            rider.active_order_count(),
            PathPlanner.euclidean(rider.position, order.res_pos),
            rider.rider_id,
        )
        if best_key is None or key < best_key:
            best = rider
            best_key = key
    return best


class OrderManager:
    """Creates orders, assigns them to riders and reports the planned route.

    Attributes:
        system: The SystemManager used for rider recruitment.
    """

    def __init__(self, system: Any) -> None:
        """Bind the manager to a SystemManager.

        Args:
            system: SystemManager instance providing ``maybe_recruit``.
        """
        self.system = system

    @staticmethod
    def all_orders() -> List[Order]:
        """Return the list of every order created so far."""
        orders = globalvar.get_value("orders")
        if orders is None:
            orders = []
            globalvar.set_value("orders", orders)
        return orders

    def pending_orders(self) -> List[Order]:
        """Return orders that have not yet been assigned to a rider."""
        return [o for o in self.all_orders() if o.status == ORDER_PENDING]

    @staticmethod
    def _validate(value: int, label: str) -> int:
        """Validate a raw coordinate against the accepted input range."""
        if not isinstance(value, int) or isinstance(value, bool):
            raise ValueError(f"{label} must be an integer.")
        if not COORD_MIN <= value <= COORD_MAX:
            raise ValueError(
                f"{label} = {value} is out of range {COORD_MIN}-{COORD_MAX}."
            )
        return value

    def create_order(self, res_x: int, res_y: int, cus_x: int, cus_y: int) -> Order:
        """Validate coordinates, create an order and register it.

        Args:
            res_x: Restaurant x coordinate.
            res_y: Restaurant y coordinate.
            cus_x: Customer x coordinate.
            cus_y: Customer y coordinate.

        Returns:
            The newly created pending Order.

        Raises:
            ValueError: If any coordinate is not an integer in range.
        """
        self._validate(res_x, "restaurant_x")
        self._validate(res_y, "restaurant_y")
        self._validate(cus_x, "customer_x")
        self._validate(cus_y, "customer_y")
        order = Order((res_x, res_y), (cus_x, cus_y))
        self.all_orders().append(order)
        logger.info("Created order %s res=%s cus=%s", order.id, order.res_pos, order.cus_pos)
        return order

    def assign(self, order: Order, rider: Rider) -> None:
        """Assign an order to a rider.

        Args:
            order: Pending order to assign.
            rider: Rider receiving the order.
        """
        order.assign_to(rider.rider_id)
        rider.orders.append(order)
        rider.on_order_assigned(order)
        logger.info("Order %s assigned to rider %s", order.id, rider.rider_id)

    def submit(self, res_x: int, res_y: int, cus_x: int, cus_y: int) -> Dict[str, Any]:
        """Create an order, possibly recruit a rider, and assign it.

        Args:
            res_x: Restaurant x coordinate.
            res_y: Restaurant y coordinate.
            cus_x: Customer x coordinate.
            cus_y: Customer y coordinate.

        Returns:
            Dictionary with keys: "order", "restaurant", "customer",
            "new_rider" (Rider or None), "rider" (Rider or None), "route"
            (list of points), "distance" (int) and "eta" (ticks or None).
        """
        order = self.create_order(res_x, res_y, cus_x, cus_y)
        new_rider = self.system.maybe_recruit(len(self.pending_orders()))
        rider = find_best_rider_for_order(order)
        result: Dict[str, Any] = {
            "order": order,
            "restaurant": order.res_pos,
            "customer": order.cus_pos,
            "new_rider": new_rider,
            "rider": None,
            "route": [],
            "distance": 0,
            "eta": None,
        }
        if rider is None:
            logger.warning("No rider available for order %s; left pending", order.id)
            return result
        self.assign(order, rider)
        route = PathPlanner.route(rider.position, rider.route_targets())
        distance = PathPlanner.path_length(route)
        eta = math.ceil(distance / rider.speed) if rider.speed > 0 else None
        result.update(rider=rider, route=route, distance=distance, eta=eta)
        return result

    @staticmethod
    def map_limit() -> int:
        """Return the maximum map coordinate."""
        return MAP_SIZE
