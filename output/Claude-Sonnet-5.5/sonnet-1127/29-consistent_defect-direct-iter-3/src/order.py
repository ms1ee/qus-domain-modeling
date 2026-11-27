"""Order assignment."""
import globalvar


def find_best_rider_for_order(order):
    """Pick rider with fewest pending orders, ties by distance."""
    riders = globalvar.get_value("riders", []) or []
    if not riders:
        return None

    def key(r):
        d = ((r.x - order.res_pos[0]) ** 2
             + (r.y - order.res_pos[1]) ** 2) ** 0.5
        return (r.pending_count(), d, r.rider_id)

    return min(riders, key=key)


def assign_order(order):
    """Assign order to best rider."""
    rider = find_best_rider_for_order(order)
    if rider is None:
        return None
    order.assign_to(rider.rider_id)
    rider.orders.append(order)
    return rider
