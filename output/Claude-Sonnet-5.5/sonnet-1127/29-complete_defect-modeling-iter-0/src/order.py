"""Order assignment."""
import globalvar
from pathplanner import PathPlanner


def find_best_rider_for_order(order):
    """Return the closest rider (ties: fewer orders), or None."""
    riders = globalvar.get_value("riders", []) or []
    best = None
    best_key = None
    for r in riders:
        key = (PathPlanner.distance(r.pos, order.res_pos), len(r.orders))
        if best_key is None or key < best_key:
            best, best_key = r, key
    return best


def assign_order(order):
    """Assign order to best rider; returns the rider or None."""
    rider = find_best_rider_for_order(order)
    if rider is not None:
        rider.orders.append(order)
        order.assign_to(rider.rider_id)
    return rider
