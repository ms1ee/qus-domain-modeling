"""Order assignment."""
import globalvar
from system import SystemManager


def find_best_rider_for_order(order):
    """Pick the rider with the lowest load, then nearest to restaurant."""
    riders = globalvar.get_value("riders")
    if riders is None:
        riders = []
        globalvar.set_value("riders", riders)
    idle = [r for r in riders if not r.orders]
    if not idle:
        new = SystemManager.recruit()
        if new is not None:
            return new
    if not riders:
        return None

    def key(r):
        d = abs(r.x - order.res_pos[0]) + abs(r.y - order.res_pos[1])
        return (len(r.orders), d, r.rider_id)

    return min(riders, key=key)
