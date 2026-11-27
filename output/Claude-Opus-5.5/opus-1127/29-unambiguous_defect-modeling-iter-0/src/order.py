"""Order creation, assignment and completion handling."""

import logging

import globalvar
import system
from order_model import Order
from path_planner import PathPlanner, manhattan
from rider import RiderState

logger = logging.getLogger(__name__)


def find_best_rider_for_order(order):
    """Select the most suitable rider for ``order``.

    Strategy:
      1. The idle rider closest (Manhattan distance) to the restaurant.
      2. Otherwise, recruit a new rider if funds and limits allow.
      3. Otherwise, the busy rider able to reach the restaurant soonest
         (remaining work + distance from its final stop), which balances load.

    Returns:
        A Rider, or None if no rider exists and none can be recruited.
    """
    riders = system.get_riders()
    target = PathPlanner.access_point(order.res_pos)
    idle = [r for r in riders if r.state == RiderState.IDLE and not r.orders]
    if idle:
        return min(idle, key=lambda r: (manhattan(r.position, target), r.rider_id))
    new_rider = system.recruit_rider()
    if new_rider is not None:
        return new_rider
    if not riders:
        return None
    return min(riders, key=lambda r: (
        r.remaining_work() + manhattan(r.final_position(), target),
        len(r.orders), r.rider_id))


class OrderManager:
    """Handles order creation, assignment and completion queries."""

    @staticmethod
    def create_order(coords):
        """Create an order from ``[rx, ry, cx, cy]`` (validated 0-800)."""
        if len(coords) != 4:
            raise ValueError("exactly four coordinates are required")
        values = []
        for c in coords:
            v = int(c)
            if v < 0 or v > 800:
                raise ValueError("coordinate %d out of range 0-800" % v)
            values.append(v)
        return Order((values[0], values[1]), (values[2], values[3]))

    @staticmethod
    def assign_order(order):
        """Assign ``order`` to the best rider.

        Returns:
            (rider, recruited) -- recruited is True if a new rider was hired.
        """
        before = len(system.get_riders())
        rider = find_best_rider_for_order(order)
        recruited = len(system.get_riders()) > before
        if rider is None:
            logger.warning("No rider available for order %d", order.id)
            return None, recruited
        rider.orders.append(order)
        order.assign_to(rider.rider_id)
        return rider, recruited

    @staticmethod
    def all_orders():
        """All orders ever created."""
        return list(globalvar.get_value("orders", []) or [])

    @staticmethod
    def completed_orders():
        """Orders that have been delivered."""
        return [o for o in OrderManager.all_orders() if o.completed]

    @staticmethod
    def pending_orders():
        """Orders not yet delivered."""
        return [o for o in OrderManager.all_orders() if not o.completed]

    @staticmethod
    def efficiency_stats():
        """Return (completed_count, average_time, average_distance)."""
        done = OrderManager.completed_orders()
        if not done:
            return 0, 0.0, 0.0
        avg_t = sum(o.time_taken or 0 for o in done) / float(len(done))
        avg_d = sum(o.distance for o in done) / float(len(done))
        return len(done), avg_t, avg_d
