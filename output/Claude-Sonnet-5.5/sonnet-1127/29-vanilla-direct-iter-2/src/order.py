"""Order assignment."""
import math
import globalvar


def find_best_rider_for_order(order):
    """Return the nearest rider (recruiting if none exists), or None."""
    riders = globalvar.get_value("riders", [])
    if not riders and globalvar.get_value("funds", 0) >= 300:
        import system
        system.create_rider()
        riders = globalvar.get_value("riders", [])
    if not riders:
        return None
    rx, ry = order.res_pos
    return min(riders, key=lambda r: (math.hypot(r.x - rx, r.y - ry),
                                      len(r.orders)))
