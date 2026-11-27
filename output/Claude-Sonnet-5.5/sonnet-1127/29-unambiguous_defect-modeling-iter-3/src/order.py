"""Order assignment."""
import globalvar


def find_best_rider_for_order(order):
    """Pick the nearest, least loaded rider; recruit one if none exist."""
    riders = globalvar.get_value("riders") or []
    if not riders:
        import system
        r = system.recruit_rider()
        riders = [r] if r else []
    if not riders:
        return None

    def key(r):
        d = abs(r.x - order.res_pos[0]) + abs(r.y - order.res_pos[1])
        return (len(r.orders), d, r.rider_id)
    return min(riders, key=key)


def assign_order(order):
    """Assign order to best rider (recruiting when all are busy)."""
    import system
    rider = find_best_rider_for_order(order)
    added = False
    if rider is not None and rider.orders:
        new = system.recruit_rider()
        if new:
            rider, added = new, True
    if rider is None:
        return None, False
    order.assign_to(rider.rider_id)
    rider.orders.append(order)
    globalvar.get_value("orders").append(order)
    return rider, added
