"""Rider model: movement, state machine and event log."""

import logging

import globalvar
from config import get_config_value
from path_planner import PathPlanner

logger = logging.getLogger("dispatch.rider")

IDLE = 0
PICKING_UP = 1
DELIVERING = 2

STATE_NAMES = {IDLE: "idle", PICKING_UP: "picking up",
               DELIVERING: "delivering"}


class Rider:
    """A delivery rider.

    Attributes:
        rider_id: unique id.
        x, y: current coordinates.
        speed: movement units per tick.
        state: 0 idle, 1 picking up, 2 delivering.
        orders: assigned (not yet completed) orders.  Assign an order by
            appending it to this list.
        special_case: True while following a special-case detour route.
        log: list of event dicts (keys include "event" and "order_id").
    """

    def __init__(self, rider_id, x=None, y=None, speed=None):
        self.rider_id = int(rider_id)
        self.x = int(x if x is not None else get_config_value("rider_start_x"))
        self.y = int(y if y is not None else get_config_value("rider_start_y"))
        self.speed = int(speed if speed is not None
                         else get_config_value("rider_speed"))
        if self.speed <= 0:
            self.speed = 1
        self.state = IDLE
        self.orders = []
        self.special_case = False
        self.path = []
        self.current_order = None
        self.completed_orders = []
        self.distance_travelled = 0
        self.log = []
        self._log_event("spawn", None)

    # ------------------------------------------------------------------ #
    # helpers
    # ------------------------------------------------------------------ #
    @staticmethod
    def _now():
        return globalvar.get_value("time", 0) or 0

    def _log_event(self, event, order):
        entry = {
            "event": event,
            "order_id": getattr(order, "id", None) if order is not None
            else None,
            "time": self._now(),
            "x": self.x,
            "y": self.y,
            "state": self.state,
        }
        self.log.append(entry)
        logger.debug("Rider %s: %s", self.rider_id, entry)

    def _next_order(self):
        for o in self.orders:
            if getattr(o, "status", None) != "completed":
                return o
        return None

    def pending_orders(self):
        """Orders not yet completed."""
        return [o for o in self.orders
                if getattr(o, "status", None) != "completed"]

    def is_available(self):
        """True if idle with no pending work."""
        return self.state == IDLE and not self.pending_orders()

    @property
    def state_name(self):
        return STATE_NAMES.get(self.state, "unknown")

    def _set_path(self, target):
        self.path, self.special_case = PathPlanner.plan_with_info(
            (self.x, self.y), target)

    def _advance(self):
        """Move along the current path by ``speed``; True if path finished."""
        budget = self.speed
        while budget > 0 and self.path:
            tx, ty = self.path[0]
            d = abs(tx - self.x) + abs(ty - self.y)
            if d <= budget:
                self.x, self.y = tx, ty
                self.path.pop(0)
                budget -= d
                self.distance_travelled += d
            else:
                if tx != self.x:
                    self.x += budget if tx > self.x else -budget
                else:
                    self.y += budget if ty > self.y else -budget
                self.distance_travelled += budget
                budget = 0
        return not self.path

    # ------------------------------------------------------------------ #
    # simulation
    # ------------------------------------------------------------------ #
    def move(self):
        """Advance the rider by one tick.

        Handles state transitions (idle -> picking up -> delivering -> idle)
        and logs the corresponding events.
        """
        if self.state == IDLE:
            order = self._next_order()
            if order is None:
                return
            self.current_order = order
            self.state = PICKING_UP
            if getattr(order, "rider_id", None) is None and hasattr(
                    order, "assign_to"):
                order.assign_to(self.rider_id)
            order.status = "picking_up"
            self._log_event("accepted_order", order)
            self._set_path(order.res_pos)

        order = self.current_order
        if order is None:
            # Inconsistent state: recover.
            self.state = IDLE
            self.path = []
            return

        if self.state == PICKING_UP:
            if self._advance():
                self.state = DELIVERING
                order.status = "delivering"
                order.pickup_time = self._now()
                self._log_event("arrived_at_merchant", order)
                self._set_path(order.cus_pos)
            return

        if self.state == DELIVERING:
            if self._advance():
                now = self._now()
                if hasattr(order, "mark_completed"):
                    order.mark_completed(now)
                else:
                    order.status = "completed"
                self.state = IDLE
                self._log_event("delivered_to_customer", order)
                if order in self.orders:
                    self.orders.remove(order)
                self.completed_orders.append(order)
                self.current_order = None
                self.special_case = False
                self.path = []

    # ------------------------------------------------------------------ #
    # estimates
    # ------------------------------------------------------------------ #
    def planned_route(self, extra_order=None):
        """Polyline of the rider's full planned route (optionally with an
        extra order appended at the end)."""
        pts = [(self.x, self.y)]
        cur = (self.x, self.y)

        def extend(target):
            nonlocal cur
            pts.extend(PathPlanner.plan(cur, target))
            cur = tuple(target)

        if self.current_order is not None and self.state != IDLE:
            pts.extend(self.path)
            if self.path:
                cur = tuple(self.path[-1])
            if self.state == PICKING_UP:
                extend(self.current_order.cus_pos)
        pending = [o for o in self.pending_orders()
                   if o is not self.current_order]
        if extra_order is not None and all(o is not extra_order
                                           for o in pending):
            pending.append(extra_order)
        for o in pending:
            extend(o.res_pos)
            extend(o.cus_pos)
        return pts

    def estimated_workload(self, extra_order=None):
        """Remaining route length including an optional extra order."""
        return PathPlanner.polyline_length(self.planned_route(extra_order))

    def to_dict(self):
        """Serialisable representation."""
        return {
            "rider_id": self.rider_id,
            "x": self.x,
            "y": self.y,
            "speed": self.speed,
            "state": self.state,
            "orders": [getattr(o, "id", None) for o in self.orders],
            "completed_orders": [getattr(o, "id", None)
                                 for o in self.completed_orders],
            "special_case": self.special_case,
            "distance_travelled": self.distance_travelled,
            "log": list(self.log),
        }

    def __repr__(self):
        return "Rider(id=%s, pos=(%s,%s), state=%s, orders=%d)" % (
            self.rider_id, self.x, self.y, self.state, len(self.orders))
