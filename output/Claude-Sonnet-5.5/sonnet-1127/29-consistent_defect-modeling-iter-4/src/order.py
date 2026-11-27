"""Order assignment."""
import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import globalvar  # noqa: E402


def find_best_rider_for_order(order):
    """Rider with fewest current orders; ties by distance to restaurant."""
    riders = globalvar.get_value("riders") or []
    if not riders:
        return None

    def key(r):
        d = math.hypot(r.x - order.res_pos[0], r.y - order.res_pos[1])
        return (r.pending_count(), d, r.rider_id)

    return min(riders, key=key)


def assign_order(order):
    """Assign order to best rider; returns rider or None."""
    rider = find_best_rider_for_order(order)
    if rider is not None:
        rider.orders.append(order)
        order.assign_to(rider.rider_id)
    return rider
