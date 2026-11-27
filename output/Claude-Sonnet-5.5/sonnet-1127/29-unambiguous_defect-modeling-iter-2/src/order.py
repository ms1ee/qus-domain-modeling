"""Order assignment."""
import globalvar
from pathplanner import PathPlanner
import system


def find_best_rider_for_order(order):
    """Pick the best rider; recruit one if none idle and funds allow."""
    riders = globalvar.get_value("riders")
    idle = [r for r in riders if r.state == 0 and not r.orders]
    if idle:
        return min(idle, key=lambda r: (
            PathPlanner.distance(r.pos, order.res_pos), r.rider_id))
    new = system.recruit_rider()
    if new is not None:
        return new
    if not riders:
        return None
    return min(riders, key=lambda r: (
        len(r.orders), PathPlanner.distance(r.pos, order.res_pos),
        r.rider_id))


def assign_order(order):
    """Find a rider, assign the order. Returns (rider, new_rider_added)."""
    before = len(globalvar.get_value("riders"))
    rider = find_best_rider_for_order(order)
    if rider is None:
        return None, False
    rider.orders.append(order)
    order.assign_to(rider.rider_id)
    globalvar.get_value("orders").append(order)
    return rider, len(globalvar.get_value("riders")) > before
