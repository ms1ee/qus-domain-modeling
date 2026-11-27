"""Rider model: movement, state transitions and status-change log."""

import logging

import globalvar
from path_planner import PathPlanner, is_street, clamp, CELL_SIZE

logger = logging.getLogger(__name__)

DEFAULT_SPEED = 50
DEFAULT_START = (400, 400)


class RiderState:
    """Rider state enumeration."""

    IDLE = 0
    PICKING_UP = 1
    DELIVERING = 2

    NAMES = {0: "idle", 1: "picking up", 2: "delivering"}

    @classmethod
    def name(cls, state):
        """Human-readable state name."""
        return cls.NAMES.get(state, "unknown")


class Rider:
    """A delivery rider.

    Orders are assigned by appending them to ``rider.orders``; the rider
    processes them in FIFO order when :meth:`move` is called.
    """

    def __init__(self, rider_id, x=None, y=None, speed=None):
        self.rider_id = int(rider_id)
        start = globalvar.get_value("start_pos", DEFAULT_START) or DEFAULT_START
        sx = int(start[0]) if x is None else int(x)
        sy = int(start[1]) if y is None else int(y)
        sx, sy = clamp(sx), clamp(sy)
        if not is_street(sx, sy):
            # snap onto the nearest vertical street so we start on a road
            sx = clamp(int(round(sx / CELL_SIZE)) * CELL_SIZE)
        self.x = sx
        self.y = sy
        if speed is None:
            speed = globalvar.get_value("default_speed", DEFAULT_SPEED)
        self.speed = max(1, int(speed or DEFAULT_SPEED))
        self.state = RiderState.IDLE
        self.orders = []
        self.special_case = False
        self.log = []
        self.route = []
        self.completed_orders = []
        self.distance_traveled = 0
        self._local_tick = 0
        self._planner = PathPlanner()
        self._record("spawn", None)

    # ------------------------------------------------------------------ utils
    @property
    def position(self):
        """Current position as a tuple."""
        return (self.x, self.y)

    @property
    def state_name(self):
        """Readable state."""
        return RiderState.name(self.state)

    def _now(self):
        tick = globalvar.get_value("tick")
        return tick if isinstance(tick, int) else self._local_tick

    def _record(self, event, order_id):
        entry = {
            "time": self._now(),
            "event": event,
            "order_id": order_id,
            "x": self.x,
            "y": self.y,
            "state": self.state,
        }
        self.log.append(entry)
        logger.debug("Rider %s: %s", self.rider_id, entry)

    def _plan_to(self, target):
        self.route = self._planner.plan(self.position, target)
        self.special_case = self._planner.special_case

    def current_target(self):
        """Return the point the rider is currently heading to (or None)."""
        if not self.orders:
            return None
        order = self.orders[0]
        if self.state == RiderState.DELIVERING:
            return tuple(order.cus_pos)
        return tuple(order.res_pos)

    def final_destination(self):
        """Position at which the rider will be after all queued orders."""
        if self.orders:
            return tuple(self.orders[-1].cus_pos)
        return self.position

    # --------------------------------------------------------------- movement
    def _advance(self, budget):
        """Move along the route spending at most ``budget`` units."""
        while budget > 0 and self.route:
            wx, wy = self.route[0]
            dist = abs(wx - self.x) + abs(wy - self.y)
            if dist <= budget:
                self.x, self.y = wx, wy
                budget -= dist
                self.distance_traveled += dist
                self.route.pop(0)
            else:
                if wx != self.x:
                    step = min(budget, abs(wx - self.x))
                    self.x += step if wx > self.x else -step
                else:
                    step = min(budget, abs(wy - self.y))
                    self.y += step if wy > self.y else -step
                self.distance_traveled += step
                budget -= step
        return budget

    def _accept(self, order):
        self.state = RiderState.PICKING_UP
        if getattr(order, "rider_id", None) is None and hasattr(order, "assign_to"):
            order.assign_to(self.rider_id)
        if hasattr(order, "mark_picking_up"):
            order.mark_picking_up(self._now())
        self._record("accepted_order", getattr(order, "id", None))
        self._plan_to(tuple(order.res_pos))

    def _arrive_merchant(self, order):
        self.state = RiderState.DELIVERING
        if hasattr(order, "mark_picked_up"):
            order.mark_picked_up(self._now())
        self._record("arrived_at_merchant", getattr(order, "id", None))
        self._plan_to(tuple(order.cus_pos))

    def _deliver(self, order):
        if hasattr(order, "mark_completed"):
            order.mark_completed(self._now())
        else:
            order.status = "completed"
        self.orders.pop(0)
        self.state = RiderState.IDLE
        self.route = []
        self.special_case = False
        self.completed_orders.append(getattr(order, "id", None))
        self._record("delivered_to_customer", getattr(order, "id", None))

    def move(self):
        """Advance the rider by one tick.

        Handles state transitions (idle -> picking up -> delivering -> idle)
        and logs them.
        """
        self._local_tick += 1
        if not self.orders:
            if self.state != RiderState.IDLE:
                self.state = RiderState.IDLE
                self.route = []
            return
        budget = self.speed
        if self.state == RiderState.IDLE:
            self._accept(self.orders[0])
        max_iterations = 2 * len(self.orders) + 4
        for _ in range(max_iterations):
            order = self.orders[0]
            target = (tuple(order.res_pos) if self.state == RiderState.PICKING_UP
                      else tuple(order.cus_pos))
            if self.position != target:
                if not self.route:
                    self._plan_to(target)
                budget = self._advance(budget)
            if self.position != target:
                break
            if self.state == RiderState.PICKING_UP:
                self._arrive_merchant(order)
            else:
                self._deliver(order)
                if not self.orders:
                    break
                self._accept(self.orders[0])

    # ------------------------------------------------------------ persistence
    def to_dict(self):
        """Serialise the rider to a dict."""
        return {
            "rider_id": self.rider_id,
            "x": self.x,
            "y": self.y,
            "speed": self.speed,
            "state": self.state,
            "orders": [getattr(o, "id", None) for o in self.orders],
            "special_case": self.special_case,
            "completed_orders": list(self.completed_orders),
            "distance_traveled": self.distance_traveled,
            "log": list(self.log),
        }

    def __repr__(self):
        return ("Rider(id=%d, pos=(%d,%d), state=%s, orders=%d)"
                % (self.rider_id, self.x, self.y, self.state_name,
                   len(self.orders)))
