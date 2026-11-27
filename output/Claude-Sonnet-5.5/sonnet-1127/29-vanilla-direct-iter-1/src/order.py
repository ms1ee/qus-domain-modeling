"""Order management: creation and assignment."""
import math

import globalvar
import system
from order_model import Order


def find_best_rider_for_order(order):
    """Return the closest rider to the restaurant (None if no riders)."""
    riders = globalvar.get_value("riders")
    if not riders:
        return None
    rx, ry = order.res_pos
    return min(riders, key=lambda r: (math.hypot(r.x - rx, r.y - ry),
                                      len(r.orders), r.rider_id))


class OrderManager:
    """Handles order creation, assignment, completion."""

    @staticmethod
    def create_order(coords):
        """Create and assign an order. Returns (order, rider, recruited)."""
        order = Order((coords[0], coords[1]), (coords[2], coords[3]))
        riders = globalvar.get_value("riders")
        idle = sum(1 for r in riders if r.state == 0 and not r.orders)
        pending = 1 + sum(1 for o in globalvar.get_value("orders")
                          if o.status == "pending")
        recruited = False
        if globalvar.get_value("funds") >= 300 and pending > idle:
            recruited = system.recruit_rider() is not None
        rider = find_best_rider_for_order(order)
        globalvar.get_value("orders").append(order)
        if rider is None:
            return order, None, recruited
        order.assign_to(rider.rider_id)
        rider.orders.append(order)
        return order, rider, recruited
