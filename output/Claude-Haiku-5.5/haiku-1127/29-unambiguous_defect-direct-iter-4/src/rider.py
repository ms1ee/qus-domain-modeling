"""Rider model: state machine, movement along streets and event logging."""

import logging

import globalvar
from path_planner import PathPlanner, all_intersections

logger = logging.getLogger(__name__)

IDLE = 0
PICKING_UP = 1
DELIVERING = 2
STATE_NAMES = {IDLE: "idle", PICKING_UP: "picking up", DELIVERING: "delivering"}

BASE_SPEED = 50
SPEED_STEP = 10
SPEED_VARIANTS = 4


def _current_tick():
    """Return the current simulated tick from the global store."""
    return globalvar.get_value("tick") or 0


def _spawn_point(rider_id):
    """Pick a deterministic starting intersection (on a road) for a rider."""
    nodes = all_intersections()
    return nodes[(rider_id * 17) % len(nodes)]


class Rider:
    """A delivery rider that moves on the street grid and serves orders.

    Attributes:
        rider_id: Unique identifier.
        x, y: Current position in map units.
        speed: Movement budget in units per tick.
        state: 0=idle, 1=picking up, 2=delivering.
        orders: Assigned orders; the first one is currently being served.
        special_case: True while the rider is yielding or in a special state.
        target: Current destination point or None.
        waypoints: Remaining route points toward ``target``.
        distance_travelled: Total distance moved.
        wait_ticks: Number of ticks spent yielding to other riders.
        log: List of dict entries with keys ``event`` and ``order_id``.
    """

    def __init__(self, rider_id):
        """Create a rider on a road with a reasonable speed, in idle state.

        Args:
            rider_id: Unique integer identifier.
        """
        self.rider_id = int(rider_id)
        self.x, self.y = _spawn_point(self.rider_id)
        self.speed = BASE_SPEED + SPEED_STEP * (self.rider_id % SPEED_VARIANTS)
        self.state = IDLE
        self.orders = []
        self.special_case = False
        self.target = None
        self.waypoints = []
        self.distance_travelled = 0
        self.wait_ticks = 0
        self.log = []
        self._record("spawn", None)
        logger.info("Rider %s spawned at (%s, %s)", self.rider_id, self.x, self.y)

    @property
    def position(self):
        """Current position as an ``(x, y)`` tuple."""
        return (self.x, self.y)

    @property
    def state_name(self):
        """Human-readable state name."""
        return STATE_NAMES.get(self.state, "unknown")

    def is_available(self):
        """Return True if the rider is idle and has no assigned orders."""
        return self.state == IDLE and not self.orders

    def set_route(self, destination):
        """Plan a street-first route from the current position to ``destination``.

        Args:
            destination: Target ``(x, y)`` point.
        """
        self.target = (int(destination[0]), int(destination[1]))
        self.waypoints = PathPlanner().plan(self.position, self.target)

    def move(self):
        """Advance the rider by one tick.

        Performs state transitions:
            * Idle -> Picking up when an order is assigned (``accepted_order``).
            * Picking up -> Delivering on reaching the restaurant
              (``arrived_at_merchant``).
            * Delivering -> Idle on reaching the customer
              (``delivered_to_customer``).
        """
        if self.state != IDLE and not self.orders:
            logger.warning("Rider %s had no orders while in state %s; resetting",
                           self.rider_id, self.state)
            self._reset_to_idle()

        if self.state == IDLE:
            if not self.orders:
                self.special_case = False
                return
            order = self.orders[0]
            order.status = "picking_up"
            self.state = PICKING_UP
            self.set_route(order.res_pos)
            self._record("accepted_order", order.id)

        if self.state in (PICKING_UP, DELIVERING):
            self._advance()

        if self.state == PICKING_UP and self.position == self.target:
            order = self.orders[0]
            order.pickup_time = _current_tick()
            order.status = "delivering"
            self.state = DELIVERING
            self._record("arrived_at_merchant", order.id)
            self.set_route(order.cus_pos)
        elif self.state == DELIVERING and self.position == self.target:
            self._complete_current_order()

    def _advance(self):
        """Spend the speed budget moving along the waypoint list."""
        budget = self.speed
        moved = 0
        while budget > 0 and self.waypoints:
            nxt = self.waypoints[0]
            if self.position == nxt:
                self.waypoints.pop(0)
                continue
            if self._is_blocked(nxt):
                self.special_case = True
                self.wait_ticks += 1
                break
            self.special_case = False
            dx = nxt[0] - self.x
            dy = nxt[1] - self.y
            if dx:
                step = min(budget, abs(dx))
                self.x += step if dx > 0 else -step
            else:
                step = min(budget, abs(dy))
                self.y += step if dy > 0 else -step
            budget -= step
            moved += step
        if moved:
            self.distance_travelled += moved
            for order in self.orders:
                order.distance += moved

    def _is_blocked(self, point):
        """Check whether a higher-priority moving rider occupies ``point``.

        Priority is given by rider id (lower id goes first). Only moving riders
        block others, so a chain of waits always ends and deadlock cannot occur.
        """
        for other in globalvar.get_value("riders") or []:
            if other is self or other.rider_id > self.rider_id:
                continue
            if other.state == IDLE:
                continue
            if other.position == point:
                return True
        return False

    def _complete_current_order(self):
        """Finish the order being delivered and release the rider."""
        order = self.orders.pop(0)
        fee = order.mark_completed(_current_tick())
        funds = globalvar.get_value("funds") or 0
        globalvar.set_value("funds", funds + fee)
        self._reset_to_idle()
        self._record("delivered_to_customer", order.id)

    def _reset_to_idle(self):
        """Return the rider to the idle state and clear the route."""
        self.state = IDLE
        self.target = None
        self.waypoints = []
        self.special_case = False

    def _record(self, event, order_id):
        """Append a status-change entry to the rider's log."""
        self.log.append({
            "time": _current_tick(),
            "event": event,
            "order_id": order_id,
            "rider_id": self.rider_id,
            "x": self.x,
            "y": self.y,
            "state": self.state,
        })

    def to_dict(self):
        """Return a JSON-serialisable snapshot of the rider."""
        return {
            "rider_id": self.rider_id,
            "x": self.x,
            "y": self.y,
            "speed": self.speed,
            "state": self.state,
            "orders": [order.id for order in self.orders],
            "special_case": self.special_case,
        }
