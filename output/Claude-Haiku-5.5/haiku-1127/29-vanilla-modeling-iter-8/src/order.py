"""Order assignment: selects the best rider for an order."""

import logging
import math
from typing import Optional

import globalvar
from rider import Rider

logger = logging.getLogger(__name__)


def euclidean_distance(x1: float, y1: float, x2: float, y2: float) -> float:
    """Return the Euclidean distance between two points."""
    return math.sqrt((x1 - x2) ** 2 + (y1 - y2) ** 2)


def find_best_rider_for_order(order) -> Optional[Rider]:
    """Select the rider that should receive ``order``.

    Strategy: closest rider first, by Euclidean distance from the rider's
    current position to the restaurant. Idle riders (state 0 with no
    orders) are preferred; if none exist, all riders are considered so
    that busy riders share the load. Ties are broken by fewer assigned
    orders and then by rider id.

    Args:
        order: The Order to be assigned.

    Returns:
        The chosen Rider, or None if no rider exists.
    """
    riders = globalvar.get_value("riders") or []
    if not riders:
        logger.info("No riders available for order %s", order.id)
        return None

    rest_x, rest_y = order.restaurant_pos
    idle = [r for r in riders if r.state == 0 and not r.orders]
    candidates = idle if idle else list(riders)

    best = min(
        candidates,
        key=lambda r: (
            euclidean_distance(r.x, r.y, rest_x, rest_y),
            len(r.orders),
            r.rider_id,
        ),
    )
    logger.debug("Order %s assigned candidate rider %s", order.id, best.rider_id)
    return best
