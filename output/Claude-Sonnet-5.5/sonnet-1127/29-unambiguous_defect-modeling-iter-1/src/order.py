"""Order assignment."""
import globalvar
from rider import Rider

RECRUIT_COST = 100
MAX_RIDERS = 10


def _dist(r, order):
    return abs(r.x - order.res_pos[0]) + abs(r.y - order.res_pos[1])


def recruit_rider():
    """Create a new rider if funds allow; return it or None."""
    funds = globalvar.get_value("funds", 0)
    riders = globalvar.get_value("riders")
    if riders is None:
        riders = []
        globalvar.set_value("riders", riders)
    if funds < RECRUIT_COST or len(riders) >= MAX_RIDERS:
        return None
    rid = (globalvar.get_value("rider_id_counter", 0) or 0) + 1
    globalvar.set_value("rider_id_counter", rid)
    globalvar.set_value("funds", funds - RECRUIT_COST)
    r = Rider(rid)
    riders.append(r)
    return r


def find_best_rider_for_order(order):
    """Pick the nearest, least loaded rider; recruit if none is idle."""
    riders = globalvar.get_value("riders") or []
    idle = [r for r in riders if not r.orders]
    if not idle:
        new = recruit_rider()
        if new is not None:
            return new
    pool = idle or riders
    if not pool:
        return None
    return min(pool, key=lambda r: (_dist(r, order), len(r.orders),
                                    r.rider_id))
