"""Order assignment."""
import globalvar


def find_best_rider_for_order(order):
    """Return the closest rider (idle riders and lighter loads preferred on ties)."""
    riders = globalvar.get_value("riders", [])
    if not riders:
        return None
    rx, ry = order.res_pos[0], order.res_pos[1]
    return min(riders, key=lambda r: (abs(r.x - rx) + abs(r.y - ry),
                                      len(r.orders), r.rider_id))


def create_and_assign(res_xy, cus_xy):
    """Create an order, recruit if needed, assign it. Returns (order, rider, recruited)."""
    import system
    from order_model import Order
    order = Order(res_xy, cus_xy)
    globalvar.get_value("orders").append(order)
    globalvar.set_value("funds", globalvar.get_value("funds", 0) + system.ORDER_INCOME)
    recruited = system.recruit_rider() is not None
    if not globalvar.get_value("riders"):
        system.recruit_rider(force=True)
        recruited = True
    rider = find_best_rider_for_order(order)
    order.assign_to(rider.rider_id)
    rider.orders.append(order)
    return order, rider, recruited
