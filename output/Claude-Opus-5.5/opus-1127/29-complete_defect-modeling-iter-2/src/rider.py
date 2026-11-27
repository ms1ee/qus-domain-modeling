"""Rider model: movement, state and order handling."""

import logging

import globalvar
from path_planner import PathPlanner

logger = logging.getLogger(__name__)


class RiderState:
    """Rider status enumeration."""
    IDLE = 0
    PICKING_UP = 1
    DELIVERING = 2

    NAMES = {0: "idle", 1: "picking up", 2: "delivering"}

    @classmethod
    def name(cls, state):
        """Human readable name of a state."""
        return cls.NAMES.get(state, "unknown")


class Rider:
    """A delivery rider.

    Orders are assigned by appending them to ``rider.orders``.  Each call to
    :meth:`move` advances the rider by one tick and performs all state
    transitions (with corresponding log entries).
    """

    DEFAULT_SPEED = 20

    def __init__(self, rider_id, x=0, y=0, speed=None):
        self.rider_id = rider_id
        self.x = int(x)
        self.y = int(y)
        self.speed = int(speed) if speed else self.DEFAULT_SPEED
        self.state = RiderState.IDLE
        self.orders = []
        self.special_case = False
        self.log = []
        self.path = []
        self.current_order = None
        self.distance_travelled = 0
        self._order_start_distance = 0
        self.planner = PathPlanner()
        self._log_event("spawn", None)

    # ---------------------------------------------------------------- helpers
    @staticmethod
    def _now():
        t = globalvar.get_value("tick", 0)
        return t if t is not None else 0

    def _log_event(self, event, order_id):
        self.log.append({
            "event": event,
            "order_id": order_id,
            "time": self._now(),
            "x": self.x,
            "y": self.y,
            "state": self.state,
        })

    def _pending_orders(self):
        return [o for o in self.orders
                if getattr(o, "status", None) != "completed"]

    def _queued_orders(self):
        return [o for o in self._pending_orders() if o is not self.current_order]

    def _set_path(self, target):
        points, special = self.planner.plan_path_with_flag((self.x, self.y),
                                                          target)
        self.path = points[1:]
        self.special_case = special

    # ------------------------------------------------------------- lifecycle
    def _start_order(self, order):
        self.current_order = order
        self.state = RiderState.PICKING_UP
        if getattr(order, "rider_id", None) is None:
            order.rider_id = self.rider_id
        order.status = "picking_up"
        order.accept_time = self._now()
        self._order_start_distance = self.distance_travelled
        self._set_path(order.res_pos)
        self._log_event("accepted_order", order.id)

    def _arrive_merchant(self):
        order = self.current_order
        self.state = RiderState.DELIVERING
        order.status = "delivering"
        order.pickup_time = self._now()
        self._set_path(order.cus_pos)
        self._log_event("arrived_at_merchant", order.id)

    def _deliver(self):
        order = self.current_order
        order.status = "completed"
        order.completion_time = self._now()
        order.time_taken = order.ticks_elapsed
        order.travel_distance = self.distance_travelled - self._order_start_distance
        if order in self.orders:
            self.orders.remove(order)
        self.current_order = None
        self.path = []
        self.special_case = False
        self.state = RiderState.IDLE
        self._log_event("delivered_to_customer", order.id)

    def _advance(self, budget):
        while budget > 0 and self.path:
            tx, ty = self.path[0]
            dx, dy = tx - self.x, ty - self.y
            dist = abs(dx) + abs(dy)
            if dist <= budget:
                self.x, self.y = tx, ty
                budget -= dist
                self.distance_travelled += dist
                self.path.pop(0)
            else:
                step = budget
                if dx != 0:
                    mv = min(step, abs(dx))
                    self.x += mv if dx > 0 else -mv
                    step -= mv
                if step > 0 and dy != 0:
                    mv = min(step, abs(dy))
                    self.y += mv if dy > 0 else -mv
                self.distance_travelled += budget
                budget = 0

    def move(self):
        """Advance the rider by one tick.

        Returns True if the rider was active during this tick.
        """
        if self.state == RiderState.IDLE:
            pending = self._pending_orders()
            if not pending:
                return False
            self._start_order(pending[0])
        order = self.current_order
        if order is None:
            # Inconsistent state: recover.
            logger.warning("Rider %s had no current order; resetting",
                           self.rider_id)
            self.state = RiderState.IDLE
            self.path = []
            return False
        order.ticks_elapsed += 1
        self._advance(self.speed)
        if not self.path:
            if self.state == RiderState.PICKING_UP:
                self._arrive_merchant()
            elif self.state == RiderState.DELIVERING:
                self._deliver()
        return True

    def reset(self):
        """Recover from an exceptional state (pending orders are kept)."""
        if self.current_order is not None and \
                self.current_order.status != "completed":
            self.current_order.status = "assigned"
        self.current_order = None
        self.path = []
        self.special_case = False
        self.state = RiderState.IDLE

    # ------------------------------------------------------------ estimation
    def projected_end(self):
        """Return (end_position, remaining_distance) of all committed work."""
        pos = (self.x, self.y)
        dist = 0
        if self.current_order is not None and self.state != RiderState.IDLE:
            pts = [pos] + list(self.path)
            dist += PathPlanner.path_length(pts)
            pos = pts[-1]
            if self.state == RiderState.PICKING_UP:
                dist += self.planner.distance(pos, self.current_order.cus_pos)
                pos = self.current_order.cus_pos
        for o in self._queued_orders():
            dist += self.planner.distance(pos, o.res_pos)
            dist += self.planner.distance(o.res_pos, o.cus_pos)
            pos = o.cus_pos
        return tuple(pos), dist

    def estimated_cost_to(self, pos):
        """Total distance the rider needs before reaching ``pos``."""
        end, dist = self.projected_end()
        return dist + self.planner.distance(end, pos)

    def to_dict(self):
        """Serialisable representation."""
        return {
            "rider_id": self.rider_id,
            "x": self.x,
            "y": self.y,
            "speed": self.speed,
            "state": self.state,
            "orders": [o.id for o in self.orders],
            "special_case": self.special_case,
            "log": list(self.log),
        }

    def __repr__(self):
        return "Rider(%s, (%d,%d), %s)" % (self.rider_id, self.x, self.y,
                                           RiderState.name(self.state))
