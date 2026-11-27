"""Order management: creation, coordinate conversion and assignment."""

import logging
import math

try:
    from . import config, globalvar
    from .order_model import Order
    from .path_planner import PathPlanner
    from .rider import RiderState
except ImportError:  # pragma: no cover
    import config
    import globalvar
    from order_model import Order
    from path_planner import PathPlanner
    from rider import RiderState

logger = logging.getLogger(__name__)


def convert_to_grid(value):
    """Convert a raw coordinate to the center of its grid cell.

    ``center = (v // 100) * 100 + 50``, clamped to the 8x8 map.
    """
    v = int(value)
    cell = min(max(v, 0) // config.CELL_SIZE, config.GRID_DIMENSION - 1)
    return cell * config.CELL_SIZE + config.CELL_SIZE // 2


def convert_position(x, y):
    """Convert a raw (x, y) to the grid cell center."""
    return convert_to_grid(x), convert_to_grid(y)


def euclidean_distance(a, b):
    return math.sqrt((a[0] - b[0]) ** 2 + (a[1] - b[1]) ** 2)


def manhattan_distance(a, b):
    return abs(a[0] - b[0]) + abs(a[1] - b[1])


def _active_count(rider):
    return sum(1 for o in rider.orders
               if getattr(o, "status", None) != "completed")


def _get_system():
    try:
        from . import system
    except ImportError:  # pragma: no cover
        import system
    return system.get_system()


def find_best_rider_for_order(order):
    """Return the best rider for ``order``.

    Riders with the fewest current (undelivered) orders are preferred; ties
    are broken by the straight-line distance to the restaurant and then by
    rider id.  If no rider exists, a recruitment is attempted.
    """
    riders = globalvar.get_value("riders")
    if riders is None:
        riders = []
        globalvar.set_value("riders", riders)
    if not riders:
        try:
            _get_system().recruit_rider()
        except Exception:  # pragma: no cover - defensive
            logger.exception("Automatic recruitment failed")
        riders = globalvar.get_value("riders") or []
    if not riders:
        return None
    res = (int(order.res_pos[0]), int(order.res_pos[1]))
    return min(riders, key=lambda r: (_active_count(r),
                                      euclidean_distance((r.x, r.y), res),
                                      r.rider_id))


class OrderManager:
    """Handles order creation, assignment and completion queries."""

    def __init__(self, system=None, planner=None):
        self.system = system
        self.planner = planner or PathPlanner()

    @staticmethod
    def orders():
        lst = globalvar.get_value("orders")
        if lst is None:
            lst = []
            globalvar.set_value("orders", lst)
        return lst

    def create_order(self, rx, ry, cx, cy):
        """Create an order from raw coordinates (converted to grid centers)."""
        res = convert_position(rx, ry)
        cus = convert_position(cx, cy)
        order = Order(res, cus)
        order.raw_input = [int(rx), int(ry), int(cx), int(cy)]
        self.orders().append(order)
        return order

    def pending_orders(self):
        return [o for o in self.orders() if o.status == "pending"]

    def completed_orders(self):
        return [o for o in self.orders() if o.status == "completed"]

    def get_order(self, order_id):
        for o in self.orders():
            if o.id == order_id:
                return o
        return None

    def dispatch(self, order):
        """Assign ``order`` to a rider, recruiting if required.

        Returns a dict with keys ``order``, ``rider``, ``recruited`` (Rider
        or None), ``route`` (list of points from the rider position) and
        ``estimated_time`` (ticks).
        """
        recruited = None
        if self.system is not None:
            recruited = self.system.check_recruitment()
        rider = find_best_rider_for_order(order)
        if recruited is None and rider is not None and \
                any(e["event"] == "spawn" for e in rider.log) and \
                len(rider.orders) == 0 and len(rider.log) == 1 and \
                rider.log[0]["time"] == globalvar.get_value("time", 0) and \
                self.system is not None and \
                self.system.last_recruited is rider:
            recruited = rider
        info = {"order": order, "rider": rider, "recruited": recruited,
                "route": [], "estimated_time": None}
        if rider is None:
            logger.warning("No rider available for order %s", order.id)
            return info
        order.assign_to(rider.rider_id)
        rider.orders.append(order)
        start = (rider.x, rider.y)
        stops = rider.remaining_stops()
        waypoints = self.planner.plan_multi(start, stops)
        info["route"] = [start] + waypoints
        info["estimated_time"] = self.planner.estimate_time(
            start, waypoints, rider.speed)
        info["stops"] = stops
        order.estimated_time = info["estimated_time"]
        return info

    def place_order(self, rx, ry, cx, cy):
        """Create and dispatch an order in one step."""
        order = self.create_order(rx, ry, cx, cy)
        return self.dispatch(order)
