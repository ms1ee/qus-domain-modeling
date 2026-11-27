"""Order service: creation, rider assignment and order history.

Assignment is distance-first: each candidate rider is scored by its Manhattan
distance to the restaurant plus a load penalty per assigned order. The rider
with the lowest score receives the order. A new rider is recruited when no
existing rider has spare capacity and funds allow.
"""

import logging

import config
import globalvar
import system
from order_model import Order
from path_planner import manhattan
from config import GRID_SIZE

logger = logging.getLogger(__name__)


def _check_coordinate(value):
    """Validate a single coordinate.

    Args:
        value: Value to check; must be an int in the range 0-800.

    Returns:
        int: The validated coordinate.

    Raises:
        ValueError: If the value is not an integer or is out of range.
    """
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError(f"coordinate {value!r} is not an integer")
    if not 0 <= value <= GRID_SIZE:
        raise ValueError(f"coordinate {value} out of range 0-{GRID_SIZE}")
    return value


def _order_list():
    """Return the global list of orders, creating it if necessary."""
    orders = globalvar.get_value("orders")
    if orders is None:
        orders = []
        globalvar.set_value("orders", orders)
    return orders


def create_order(coords):
    """Create an order from ``[restaurant_x, restaurant_y, customer_x, customer_y]``.

    Args:
        coords: Sequence of four integers in the range 0-800.

    Returns:
        Order: The newly created order, registered in the global order list.

    Raises:
        ValueError: If the sequence length or any coordinate is invalid.
    """
    if len(coords) != 4:
        raise ValueError("expected [restaurant_x, restaurant_y, customer_x, customer_y]")
    values = [_check_coordinate(v) for v in coords]
    order = Order((values[0], values[1]), (values[2], values[3]))
    _order_list().append(order)
    logger.info("Order %s created", order.id)
    return order


def cancel_order(order):
    """Remove an order that could not be dispatched from the global list.

    Args:
        order: Order to remove.
    """
    orders = _order_list()
    orders[:] = [o for o in orders if o is not order]


def get_all_orders():
    """Return a copy of all orders created so far.

    Returns:
        list[Order]: Orders in creation order.
    """
    return list(_order_list())


def find_best_rider_for_order(order):
    """Choose the best rider for an order (distance-first with load balancing).

    Candidate riders are those with fewer than ``max_orders_per_rider``
    assigned orders. If there are none, a new rider is recruited when
    possible. The score of a candidate is the Manhattan distance to the
    restaurant plus ``load_weight`` per assigned order; the lowest score wins,
    ties broken by rider id.

    Args:
        order: The Order that needs a rider.

    Returns:
        Rider: The selected (or newly recruited) rider.
    """
    riders = system.get_riders()
    max_orders = config.CONFIG["max_orders_per_rider"]
    load_weight = config.CONFIG["load_weight"]

    candidates = [r for r in riders if len(r.orders) < max_orders]
    if not candidates:
        new_rider = system.recruit_rider()
        if new_rider is not None:
            return new_rider
        candidates = list(riders)
    if not candidates:
        return system.recruit_rider(force=True)

    def score(rider):
        """Return the sort key for a candidate rider."""
        distance = manhattan(rider.position, order.res_pos)
        return (distance + load_weight * len(rider.orders), rider.rider_id)

    return min(candidates, key=score)


def dispatch_order(order):
    """Assign an order to the best rider and start route planning.

    Args:
        order: The Order to assign.

    Returns:
        Rider: The rider that received the order.
    """
    rider = find_best_rider_for_order(order)
    rider.orders.append(order)
    order.assign_to(rider.rider_id)
    rider.sync_orders()
    logger.info("Order %s assigned to rider %s", order.id, rider.rider_id)
    return rider
