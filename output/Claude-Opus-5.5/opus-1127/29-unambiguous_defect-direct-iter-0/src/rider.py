"""Rider model: movement, state machine and order handling."""

import logging

import globalvar
from path_planner import planner

logger = logging.getLogger(__name__)

IDLE = 0
PICKING_UP = 1
DELIVERING = 2
STATE_NAMES = {IDLE: "idle", PICKING_UP: "picking up", DELIVERING: "delivering"}


class Rider:
    """A delivery rider moving along the streets of the grid.

    Orders are assigned by appending them to :attr:`orders`. Each call to
    :meth:`move` advances the rider by one tick, performing the state
    transitions idle -> picking up -> delivering -> idle and logging them.
    """

    def __init__(self, rider_id, x=None, y=None, speed=None):
        """Create a rider with the given id at a street start location."""
        cfg = globalvar.get_value("config") or {}
        if x is None:
            x = cfg.get("rider_start_x", 400)
        if y is None:
            y = cfg.get("rider_start_y", 400)
        if speed is None:
            speed = cfg.get("rider_speed", 100)
        self.rider_id = rider_id
        self.x, self.y = planner.snap_to_road(x, y)
        self.speed = max(1, int(speed))
        self.state = IDLE
        self.orders = []
        self.special_case = False
        self.path = []
        self.target = None
        self.current_order = None
        self.log = []
        self.ticks = 0
        self.distance_travelled = 0
        self.completed_orders = 0
        self._order_start_distance = 0
        self._stuck_ticks = 0
        self._log_event("spawn", None)

    # ---------------------------------------------------------------- helpers
    def _now(self):
        """Current simulated time."""
        if isinstance(globalvar.get_value("time"), int):
            return globalvar.get_value("time")
        return self.ticks

    def _log_event(self, event, order_id):
        """Append a status-change event to the rider log."""
        self.log.append({
            "event": event,
            "order_id": order_id,
            "rider_id": self.rider_id,
            "time": self._now(),
            "x": self.x,
            "y": self.y,
            "state": self.state,
        })
        logger.debug("Rider %s %s order=%s at (%s,%s)", self.rider_id, event,
                     order_id, self.x, self.y)

    def active_orders(self):
        """Orders that are not completed yet."""
        return [o for o in self.orders
                if getattr(o, "status", None) != "completed"]

    def is_idle(self):
        """True if the rider is idle and has no outstanding orders."""
        return self.state == IDLE and not self.active_orders()

    @property
    def state_name(self):
        """Human readable state name."""
        return STATE_NAMES.get(self.state, "unknown")

    def _reset_idle(self):
        """Return to idle state, dropping the current target."""
        self.state = IDLE
        self.current_order = None
        self.target = None
        self.path = []
        self.special_case = False

    # -------------------------------------------------------------- movement
    def move(self):
        """Advance the rider by one tick."""
        self.ticks += 1
        try:
            self._move_step()
        except Exception:  # pragma: no cover - recovery path
            logger.exception("Rider %s failed to move; recovering",
                             self.rider_id)
            self.x, self.y = planner.snap_to_road(self.x, self.y)
            self.target = None
            self.path = []

    def _move_step(self):
        """Core per-tick state machine."""
        # Drop completed orders that may still be in the list.
        self.orders[:] = self.active_orders()
        if (self.current_order is not None
                and not any(o is self.current_order for o in self.orders)):
            self._reset_idle()
        if self.state not in STATE_NAMES:
            self._reset_idle()
        if self.state != IDLE and self.current_order is None:
            self._reset_idle()

        if self.state == IDLE:
            nxt = self.orders[0] if self.orders else None
            if nxt is None:
                self.special_case = False
                return
            self._accept(nxt)

        if self.state == PICKING_UP:
            if self.target is None:
                self._plan(self.current_order.res_pos)
            self._advance()
            if (self.x, self.y) == self.target:
                self._arrive_merchant()
        elif self.state == DELIVERING:
            if self.target is None:
                self._plan(self.current_order.cus_pos)
            self._advance()
            if (self.x, self.y) == self.target:
                self._deliver()

    def _plan(self, center):
        """Plan a path to the access point of the cell ``center``."""
        if not planner.is_on_road(self.x, self.y):
            self.x, self.y = planner.snap_to_road(self.x, self.y)
        pos = (self.x, self.y)
        self.special_case = planner.is_special_case(pos, center)
        point, path, _ = planner.best_access(pos, center)
        self.target = point
        self.path = list(path)
        self._stuck_ticks = 0

    def _advance(self):
        """Move up to ``speed`` units along the planned path."""
        remaining = self.speed
        before = (self.x, self.y)
        while remaining > 0 and self.path:
            tx, ty = self.path[0]
            dx, dy = tx - self.x, ty - self.y
            if dx == 0 and dy == 0:
                self.path.pop(0)
                continue
            if dx != 0:
                step = min(abs(dx), remaining)
                self.x += step if dx > 0 else -step
            else:
                step = min(abs(dy), remaining)
                self.y += step if dy > 0 else -step
            remaining -= step
            self.distance_travelled += step
        if (self.x, self.y) == before and (self.x, self.y) != self.target:
            # No progress: replan to avoid deadlocks.
            self._stuck_ticks += 1
            if self._stuck_ticks >= 1 and self.current_order is not None:
                center = (self.current_order.res_pos if self.state == PICKING_UP
                          else self.current_order.cus_pos)
                self._plan(center)

    # ------------------------------------------------------ state transitions
    def _accept(self, order):
        """Idle -> picking up."""
        self.current_order = order
        self.state = PICKING_UP
        self.target = None
        self.path = []
        if getattr(order, "rider_id", None) is None:
            order.rider_id = self.rider_id
        order.status = "picking_up"
        order.accept_time = self._now()
        self._order_start_distance = self.distance_travelled
        self._log_event("accepted_order", order.id)

    def _arrive_merchant(self):
        """Picking up -> delivering."""
        order = self.current_order
        self.state = DELIVERING
        order.status = "delivering"
        order.pickup_time = self._now()
        self.target = None
        self.path = []
        self.special_case = False
        self._log_event("arrived_at_merchant", order.id)

    def _deliver(self):
        """Delivering -> idle."""
        order = self.current_order
        now = self._now()
        order.status = "completed"
        order.complete_time = now
        start = order.start_time if order.start_time is not None else now
        order.time_taken = now - start
        order.travel_distance = self.distance_travelled - \
            self._order_start_distance
        self.orders[:] = [o for o in self.orders if o is not order]
        self.completed_orders += 1
        self._reset_idle()
        self._log_event("delivered_to_customer", order.id)

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
            "completed_orders": self.completed_orders,
            "distance_travelled": self.distance_travelled,
            "log": self.log,
        }

    def __repr__(self):
        return "Rider(id=%s, pos=(%s,%s), state=%s, orders=%d)" % (
            self.rider_id, self.x, self.y, self.state, len(self.orders))
