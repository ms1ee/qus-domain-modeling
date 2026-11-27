"""Order assignment."""
from src import globalvar


def _pending_count(rider):
    return sum(1 for o in rider.orders if o.status != "completed")


def find_best_rider_for_order(order):
    """Return rider with fewest pending orders, ties by distance."""
    riders = globalvar.get_value("riders", [])
    if not riders:
        return None
    rx, ry = order.res_pos
    return min(riders, key=lambda r: (
        _pending_count(r),
        ((r.x - rx) ** 2 + (r.y - ry) ** 2) ** 0.5))
