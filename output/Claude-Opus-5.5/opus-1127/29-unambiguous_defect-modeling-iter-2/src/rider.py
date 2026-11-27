"""Rider model: movement, state transitions and status log."""

import logging
from enum import IntEnum

import globalvar
from path_planner import PathPlanner, DEFAULT_GRID

logger = logging.getLogger(__name__)

DEFAULT_SPEED = 100

SPAWN_POINTS = [
    (400, 400), (0, 0), (800, 800), (0, 800), (800, 0),
    (400, 0), (0, 400), (800, 400), (400, 800), (200, 600),
]

_planner = PathPlanner()


class RiderState(IntEnum):
    """Rider status enumeration."""
    IDLE = 0
    PICKING_UP = 1
    DELIVERING = 2


STATE_NAMES = {0: "idle", 1: "picking up", 2: "delivering"}


class Rider:
    """A delivery rider moving along the street grid."""

    def __init__(self, rider_id, x=None, y=None, speed=None):
        self.rider_id = int(rider_id)
        if x is None or y is None:
            sx, sy = SPAWN_POINTS[(self.rider_id - 1) % len(SPAWN_POINTS)]
            x = sx if x is None else x
            y = sy if y is None else y
        self.x = DEFAULT_GRID.clamp(x)
        self.y = DEFAULT_GRID.clamp(y)
        if speed is None:
            speed = globalvar.get_value("rider_speed") or DEFAULT_SPEED
        self.speed = max(1, int(speed))
        self.state = RiderState.IDLE
        self.orders = []
        self.special_case = False
        self.route = []
        self.current_order = None
        self.completed_orders = []
        self.distance_travelled = 0
        self.log = []
        self._record("spawn", None)

    # ---------------------------------------------------------------- helpers
    @property
    def state_name(self):
        """Human readable state."""
        return STATE_NAMES.get(int(self.state), "unknown")

    def _record(self, event, order_id):
        entry = {
            "time": globalvar.get_value("tick", 0) or 0,
            "event": event,
            "order_id": order_id,
            "x": self.x,
            "y": self.y,
            "state": int(self.state),
        }
        self.log.append(entry)
        logger.debug("Rider %d: %s", self.rider_id, entry)

    def pending_orders(self):
        """Orders assigned to this rider and not yet delivered."""
        return [o for o in self.orders
                if getattr(o, "status", None) != "completed"]

    def is_available(self):
        """True if the rider is idle with no queued orders."""
        return self.state == RiderState.IDLE and not self.pending_orders()

    def final_position(self):
        """Estimated position after finishing every queued order."""
        pending = self.pending_orders()
        if not pending:
            return (self.x, self.y)
        last = pending[-1]
        if getattr(last, "dropoff_point", None):
            return tuple(last.dropoff_point)
        pickup = getattr(last, "pickup_point", None)
        if not pickup:
            pickup = _planner.best_access_point((self.x, self.y),
                                                last.res_pos)[0]
        return _planner.best_access_point(pickup, last.cus_pos)[0]

    def reset(self):
        """Recover to a consistent idle state (error recovery)."""
        if self.current_order is not None and \
                self.current_order.status != "completed":
            self.current_order.status = "assigned"
        self.state = RiderState.IDLE
        self.route = []
        self.current_order = None
        self.special_case = False

    def _advance(self):
        """Move up to ``speed`` units along the remaining route."""
        budget = self.speed
        while budget > 0 and self.route:
            tx, ty = self.route[0]
            d = abs(tx - self.x) + abs(ty - self.y)
            if d <= budget:
                self.x, self.y = tx, ty
                budget -= d
                self.distance_travelled += d
                self.route.pop(0)
            else:
                if tx != self.x:
                    self.x += budget if tx > self.x else -budget
                else:
                    self.y += budget if ty > self.y else -budget
                self.distance_travelled += budget
                budget = 0

    # -------------------------------------------------------------- lifecycle
    def _accept(self, order):
        if getattr(order, "rider_id", None) != self.rider_id:
            order.assign_to(self.rider_id)
        order.status = "picking_up"
        order.accept_time = globalvar.get_value("tick", 0) or 0
        pickup, _ = _planner.best_access_point((self.x, self.y), order.res_pos)
        order.pickup_point = pickup
        self.special_case = _planner.is_special_case((self.x, self.y), pickup)
        self.route = _planner.plan_path((self.x, self.y), pickup)[1:]
        self.current_order = order
        self.state = RiderState.PICKING_UP
        self._record("accepted_order", order.id)

    def _arrive_at_merchant(self, order):
        here = (self.x, self.y)
        dropoff, length = _planner.best_access_point(here, order.cus_pos)
        order.dropoff_point = dropoff
        order.distance = length
        order.pickup_time = globalvar.get_value("tick", 0) or 0
        order.status = "delivering"
        self.special_case = _planner.is_special_case(here, dropoff)
        self.route = _planner.plan_path(here, dropoff)[1:]
        self.state = RiderState.DELIVERING
        self._record("arrived_at_merchant", order.id)

    def _deliver(self, order):
        now = globalvar.get_value("tick", 0) or 0
        order.status = "completed"
        order.completion_time = now
        order.time_taken = now - order.start_time
        if order.time_taken > 0:
            order.efficiency = round(order.distance / float(order.time_taken), 2)
        if order in self.orders:
            self.orders.remove(order)
        self.completed_orders.append(order)
        self.current_order = None
        self.route = []
        self.special_case = False
        self.state = RiderState.IDLE
        self._record("delivered_to_customer", order.id)

    def move(self):
        """Advance the rider by one tick.

        Idle riders accept their next queued order; picking-up riders move
        towards the restaurant and switch to delivering once they reach it;
        delivering riders move to the customer and become idle on delivery.
        """
        if self.state == RiderState.IDLE:
            pending = self.pending_orders()
            if pending:
                self._accept(pending[0])
            return
        order = self.current_order
        if order is None:
            self.reset()
            return
        if self.state == RiderState.PICKING_UP:
            self._advance()
            if not self.route:
                self._arrive_at_merchant(order)
        elif self.state == RiderState.DELIVERING:
            self._advance()
            if not self.route:
                self._deliver(order)
        else:
            self.reset()

    def to_dict(self):
        """JSON-serialisable representation."""
        return {
            "rider_id": self.rider_id,
            "x": self.x,
            "y": self.y,
            "speed": self.speed,
            "state": int(self.state),
            "orders": [o.id for o in self.orders],
            "completed_orders": [o.id for o in self.completed_orders],
            "special_case": self.special_case,
            "distance_travelled": self.distance_travelled,
            "log": list(self.log),
        }

    def __repr__(self):
        return "Rider(#%d at (%d,%d) %s, %d orders)" % (
            self.rider_id, self.x, self.y, self.state_name, len(self.orders))
