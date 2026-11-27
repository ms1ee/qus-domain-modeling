"""Order creation, distance-first assignment and repair of order state."""

import logging
import math
from typing import Any, List, Optional, Tuple

import globalvar
from order_model import Order
from rider import Rider, STATE_IDLE

LOGGER = logging.getLogger("dispatch.order")


def _euclidean_distance(rider: Rider, order: Order) -> float:
    """Return sqrt((rider_x - restaurant_x)^2 + (rider_y - restaurant_y)^2)."""
    return math.sqrt((rider.x - order.restaurant_x) ** 2
                     + (rider.y - order.restaurant_y) ** 2)


def find_best_rider_for_order(order: Order) -> Optional[Rider]:
    """Choose the best rider for an order.

    Idle riders are preferred and the closest one (Euclidean distance to the
    restaurant) wins. If no rider is idle, the rider with the fewest assigned
    orders is chosen, with distance as the tie-breaker, to balance load.

    Args:
        order: The order needing a rider.

    Returns:
        The selected Rider, or None if there are no riders.
    """
    riders = globalvar.get_value("riders", []) or []
    if not riders:
        return None
    idle = [rider for rider in riders if rider.is_idle()]
    if idle:
        return min(idle, key=lambda r: _euclidean_distance(r, order))
    return min(riders,
               key=lambda r: (len(r.orders), _euclidean_distance(r, order)))


class OrderManager:
    """Creates, assigns and repairs orders.

    All order collections live in the global store: ``"orders"`` (every
    order ever created) and ``"pending_orders"`` (orders waiting for a rider).
    """

    def submit_order(self, res_pos: Tuple[int, int],
                     cus_pos: Tuple[int, int]) -> Order:
        """Create an order at the current simulated time and queue it.

        Args:
            res_pos: Restaurant (x, y) in 0-800.
            cus_pos: Customer (x, y) in 0-800.

        Returns:
            The newly created Order (status "created").
        """
        start = int(globalvar.get_value("simulated_time", 0) or 0)
        order = Order(res_pos, cus_pos, start_time=start)
        globalvar.get_value("orders").append(order)
        globalvar.get_value("pending_orders").append(order)
        LOGGER.info("Order %d submitted", order.id)
        return order

    def assign_pending(self) -> List[Tuple[Order, Rider]]:
        """Assign every pending order that can be matched to a rider.

        Returns:
            List of (order, rider) pairs assigned during this call.
        """
        assignments: List[Tuple[Order, Rider]] = []
        pending = globalvar.get_value("pending_orders")
        for order in list(pending):
            rider = find_best_rider_for_order(order)
            if rider is None:
                break
            rider.accept_order(order)
            pending.remove(order)
            assignments.append((order, rider))
            LOGGER.info("Order %d assigned to rider %d", order.id,
                        rider.rider_id)
        return assignments

    def all_orders(self) -> List[Order]:
        """Return every order created so far."""
        return list(globalvar.get_value("orders", []) or [])

    def pending_orders(self) -> List[Order]:
        """Return orders waiting for a rider."""
        return list(globalvar.get_value("pending_orders", []) or [])

    def repair_state(self) -> int:
        """Detect and fix inconsistent order/rider state.

        Fixes performed:
            * completed orders still listed on a rider are removed;
            * riders without orders are set to idle;
            * assigned orders that no rider holds return to the pending queue.

        Returns:
            Number of repairs performed.
        """
        fixes = 0
        riders = globalvar.get_value("riders", []) or []
        pending = globalvar.get_value("pending_orders", [])
        held_ids = set()
        for rider in riders:
            for order in list(rider.orders):
                if order.status == "completed":
                    rider.orders.remove(order)
                    fixes += 1
                else:
                    held_ids.add(order.id)
            if not rider.orders and rider.state != STATE_IDLE:
                rider.state = STATE_IDLE
                fixes += 1
        for order in globalvar.get_value("orders", []) or []:
            if order.status == "assigned" and order.id not in held_ids:
                order.status = "created"
                order.rider_id = None
                if order not in pending:
                    pending.append(order)
                fixes += 1
        if fixes:
            LOGGER.warning("Repaired %d inconsistent state item(s)", fixes)
        return fixes
