"""Order assignment: rider selection, recruitment and dispatching."""

import logging
import math
from typing import List, Optional, Tuple

import globalvar
import system
from order_model import Order
from rider import Rider

logger = logging.getLogger(__name__)


def euclidean_distance(x1: float, y1: float, x2: float, y2: float) -> float:
    """Return the Euclidean distance between two points.

    Args:
        x1: X coordinate of the first point.
        y1: Y coordinate of the first point.
        x2: X coordinate of the second point.
        y2: Y coordinate of the second point.

    Returns:
        ``sqrt((x1 - x2)^2 + (y1 - y2)^2)``.
    """
    return math.sqrt((x1 - x2) ** 2 + (y1 - y2) ** 2)


def find_best_rider_for_order(order: Order) -> Optional[Rider]:
    """Select the best rider to serve an order.

    Selection is closest-first by Euclidean distance from the rider to the
    restaurant. For load balancing, riders with fewer assigned orders are
    preferred first; idle riders (zero orders) therefore always win over busy
    ones, and ties are broken by rider id.

    Args:
        order: The order to be assigned.

    Returns:
        The selected rider, or None if no riders exist.
    """
    riders = globalvar.get_value("riders") or []
    if not riders:
        return None
    rx, ry = order.res_pos
    return min(
        riders,
        key=lambda r: (
            len(r.orders),
            euclidean_distance(r.x, r.y, rx, ry),
            r.rider_id,
        ),
    )


def dispatch_pending_orders() -> Tuple[List[Tuple[Order, Rider]], List[Rider]]:
    """Assign all pending orders in FIFO order, recruiting riders as needed.

    Before each assignment the recruitment rule is applied repeatedly: while
    funds allow and pending orders exceed idle riders, a new rider is created.
    Orders that cannot be assigned (no riders and insufficient funds) remain
    in the pending queue.

    Returns:
        A tuple ``(assignments, new_riders)`` where ``assignments`` is a list of
        ``(order, rider)`` pairs and ``new_riders`` lists riders recruited in
        this call.
    """
    pending = globalvar.get_value("pending_orders")
    if pending is None:
        pending = []
        globalvar.set_value("pending_orders", pending)

    assignments: List[Tuple[Order, Rider]] = []
    new_riders: List[Rider] = []

    while pending:
        order = pending[0]
        while True:
            recruited = system.recruit_if_needed(len(pending))
            if recruited is None:
                break
            new_riders.append(recruited)

        best = find_best_rider_for_order(order)
        if best is None:
            break

        order.assign_to(best.rider_id)
        pending.pop(0)
        assignments.append((order, best))

    return assignments, new_riders
