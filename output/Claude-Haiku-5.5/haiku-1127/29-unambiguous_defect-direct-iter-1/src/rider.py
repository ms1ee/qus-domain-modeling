"""Rider model: state machine, street movement and stop handling.

A rider's assigned orders are stored in ``rider.orders``. During each tick the
rider plans routes for newly assigned orders, moves along the planned street
path using its speed, and processes pickup and delivery stops when it reaches
them. Each significant event is recorded in ``rider.log``.
"""

import logging

import config
import globalvar
from path_planner import PathPlanner, manhattan, to_lattice_point

logger = logging.getLogger(__name__)

STATE_IDLE = 0
STATE_PICKING_UP = 1
STATE_DELIVERING = 2

STATE_NAMES = {
    STATE_IDLE: "idle",
    STATE_PICKING_UP: "picking up",
    STATE_DELIVERING: "delivering",
}

DEFAULT_START = (400, 400)

_planner = PathPlanner()


class Rider:
    """A delivery rider moving on the street grid.

    Attributes:
        rider_id: Unique integer identifier.
        x, y: Current coordinates (integers, 0-800).
        speed: Movement speed in units per tick.
        state: 0 idle, 1 picking up, 2 delivering.
        orders: List of assigned Order objects.
        special_case: True while the rider moves straight toward its next
            stop (target directly above, below or beside it).
        path: Remaining lattice nodes to visit, in order.
        stops: Pending pickup/dropoff stops, each a dict with keys
            "kind", "order" and "node".
        log: List of event dicts with keys "event", "order_id", "time",
            "x", "y", "state" and "rider_id".
        distance_travelled: Total units travelled.
        deliveries: Number of completed deliveries.
    """

    def __init__(self, rider_id, start=None, speed=None):
        """Create a rider on a street intersection.

        Args:
            rider_id: Unique identifier for the rider.
            start: Optional ``(x, y)`` starting point; snapped to a street
                intersection. Defaults to the map centre.
            speed: Optional speed in units per tick. Defaults to a value chosen
                from the configured speed list by rider id.
        """
        self.rider_id = rider_id
        x, y = to_lattice_point(start if start is not None else DEFAULT_START)
        self.x = x
        self.y = y
        if speed is None:
            speeds = config.CONFIG["rider_speeds"]
            speed = speeds[rider_id % len(speeds)]
        self.speed = int(speed)
        self.state = STATE_IDLE
        self.orders = []
        self.special_case = False
        self.path = []
        self.stops = []
        self._planned_ids = set()
        self.log = []
        self.distance_travelled = 0
        self.deliveries = 0
        self._log("spawn", None)

    @property
    def position(self):
        """Return the current ``(x, y)`` position."""
        return (self.x, self.y)

    @property
    def state_name(self):
        """Return a human-readable name for the current state."""
        return STATE_NAMES.get(self.state, "unknown")

    def route_nodes(self):
        """Return the current position followed by the planned route nodes.

        Returns:
            list[tuple]: Nodes for drawing the planned route.
        """
        return [self.position] + list(self.path)

    def sync_orders(self):
        """Plan routes for newly assigned orders and update the state.

        Orders appended to ``self.orders`` that have not been planned yet are
        turned into pickup and dropoff stops, appended to the route, and
        logged as ``accepted_order``. Zero-length stops are processed
        immediately.
        """
        for order in list(self.orders):
            if order.id in self._planned_ids:
                continue
            self._plan_order(order)
            self._planned_ids.add(order.id)
            self._log("accepted_order", order.id)
        self._process_stops_here()
        self.state = self._derive_state()

    def move(self):
        """Advance the rider by one tick.

        Steps performed: plan new orders, move up to ``speed`` units along the
        route, process any stop reached, and update the state.
        """
        self.sync_orders()
        self._advance(self.speed)
        self._process_stops_here()
        self.state = self._derive_state()
        self.special_case = self._is_straight_to_target()

    def _plan_order(self, order):
        """Append pickup and dropoff legs for an order to the route.

        Args:
            order: Order object with ``res_pos`` and ``cus_pos`` attributes.
        """
        origin = self.path[-1] if self.path else self.position
        pickup = order.res_pos
        self.path.extend(_planner.plan(origin, pickup))
        self.stops.append({"kind": "pickup", "order": order, "node": pickup})

        dropoff = order.cus_pos
        self.path.extend(_planner.plan(pickup, dropoff))
        self.stops.append({"kind": "dropoff", "order": order, "node": dropoff})

    def _advance(self, budget):
        """Move along the planned path, spending at most ``budget`` units.

        Args:
            budget: Number of units the rider may travel this tick.
        """
        while budget > 0 and self.path:
            tx, ty = self.path[0]
            dx = tx - self.x
            dy = ty - self.y
            if dx == 0 and dy == 0:
                self.path.pop(0)
                self._process_stops_here()
                continue
            if dx != 0:
                step = min(budget, abs(dx)) * (1 if dx > 0 else -1)
                self.x += step
            else:
                step = min(budget, abs(dy)) * (1 if dy > 0 else -1)
                self.y += step
            moved = abs(step)
            budget -= moved
            self.distance_travelled += moved
            if (self.x, self.y) == (tx, ty):
                self.path.pop(0)
                self._process_stops_here()

    def _process_stops_here(self):
        """Handle every pending stop located at the current position."""
        while self.stops and self.stops[0]["node"] == self.position:
            stop = self.stops.pop(0)
            order = stop["order"]
            tick = self._current_tick()
            if stop["kind"] == "pickup":
                order.mark_picked_up(tick)
                self._log("arrived_at_merchant", order.id)
            else:
                self._log("delivered_to_customer", order.id)
                self._complete_order(order)

    def _complete_order(self, order):
        """Finish an order: release it from the rider and record completion.

        Args:
            order: The delivered Order object.
        """
        order.complete(self._current_tick())
        self.orders = [o for o in self.orders if o is not order]
        self._planned_ids.discard(order.id)
        self.deliveries += 1
        logger.info("Rider %s delivered order %s", self.rider_id, order.id)

    def _derive_state(self):
        """Return the state implied by the next pending stop.

        Returns:
            int: 0 when no stops remain, 1 when the next stop is a pickup,
            2 when it is a dropoff.
        """
        if not self.stops:
            return STATE_IDLE
        if self.stops[0]["kind"] == "pickup":
            return STATE_PICKING_UP
        return STATE_DELIVERING

    def _is_straight_to_target(self):
        """Return True if the next target is directly above, below or beside.

        Returns:
            bool: Whether the rider is on a straight run to its next stop.
        """
        if not self.stops:
            return False
        tx, ty = self.stops[0]["node"]
        return (tx == self.x or ty == self.y) and (tx, ty) != self.position

    def _current_tick(self):
        """Return the global simulated time."""
        return globalvar.get_value("tick", 0)

    def _log(self, event, order_id):
        """Append an event entry to the rider log.

        Args:
            event: Event name such as ``"accepted_order"``.
            order_id: Related order id, or None.
        """
        entry = {
            "event": event,
            "order_id": order_id,
            "time": self._current_tick(),
            "x": self.x,
            "y": self.y,
            "state": self.state,
            "rider_id": self.rider_id,
        }
        self.log.append(entry)
        logger.debug("Rider %s %s order=%s", self.rider_id, event, order_id)

    def to_dict(self):
        """Return a JSON-serialisable representation of the rider.

        Returns:
            dict: Rider attributes for persistence and display.
        """
        return {
            "rider_id": self.rider_id,
            "x": self.x,
            "y": self.y,
            "speed": self.speed,
            "state": self.state,
            "state_name": self.state_name,
            "order_ids": [o.id for o in self.orders],
            "special_case": self.special_case,
            "deliveries": self.deliveries,
            "distance_travelled": self.distance_travelled,
        }

    def distance_to(self, point):
        """Return the Manhattan distance from the rider to ``point``.

        Args:
            point: ``(x, y)`` target.

        Returns:
            int: Manhattan distance.
        """
        return manhattan(self.position, point)
