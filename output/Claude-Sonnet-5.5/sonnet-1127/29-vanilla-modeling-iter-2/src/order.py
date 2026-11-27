"""Order assignment."""
import globalvar


def find_best_rider_for_order(order):
    """Return the nearest rider (idle preferred), or None."""
    riders = globalvar.get_value("riders") or []
    if not riders:
        return None
    rx, ry = order.res_pos

    def key(r):
        d = ((r.x - rx) ** 2 + (r.y - ry) ** 2) ** 0.5
        return (0 if r.state == 0 and not r.orders else 1,
                len(r.orders), d)
    return min(riders, key=key)
