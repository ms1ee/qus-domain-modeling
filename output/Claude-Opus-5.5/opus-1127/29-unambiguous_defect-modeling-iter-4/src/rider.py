"""Rider model: movement, state machine and status logging."""

import logging
from enum import IntEnum

import globalvar
from config import DEFAULT_CONFIG
from grid_map import GridMap
from order_model import (Order, STATUS_COMPLETED, STATUS_DELIVERING,
                         STATUS_PICKING_UP)
from path_planner import PathPlanner

logger = logging.getLogger(__name__)


class RiderState(IntEnum):
    """Rider status enumeration."""

    IDLE = 0
    PICKING_UP = 1
    DELIVERING = 2


STATE_NAMES = {0: "idle", 1: "picking up", 2: "delivering"}


def _now():
    return int(globalvar.get_value("current_time", 0) or 0)


class Rider:
    """A delivery rider.

    Attributes:
        rider_id: Unique id.
        x, y: Current coordinates.
        speed: Units moved per tick.
        state: 0 idle, 1 picking up, 2 delivering.
        orders: Assigned orders (processed in FIFO order).
        special_case: True while following a special-case route.
        log: List of status-change dicts (keys: time, event, order_id, x, y, state).
    """

    def __init__(self, rider_id):
        cfg = globalvar.get_value("config")
        if not isinstance(cfg, dict):
            cfg = DEFAULT_CONFIG
        spawn = cfg.get("rider_spawn", DEFAULT_CONFIG["rider_spawn"])
        self.rider_id = int(rider_id)
        self.x = int(spawn[0])
        self.y = int(spawn[1])
        self.speed = max(1, int(cfg.get("rider_speed", DEFAULT_CONFIG["rider_speed"])))
        self.state = int(RiderState.IDLE)
        self.orders = []
        self.special_case = False
        self.route = []
        self.log = []
        self.distance_travelled = 0
        self.completed_orders = 0
        self._current_order = None
        self._record("spawn", None)

    # ------------------------------------------------------------------ helpers
    @property
    def position(self):
        """Current position as a tuple."""
        return (self.x, self.y)

    @property
    def state_name(self):
        """Human readable state."""
        return STATE_NAMES.get(self.state, "unknown")

    def active_orders(self):
        """Orders not yet completed."""
        return [o for o in self.orders if getattr(o, "status", None) != STATUS_COMPLETED]

    def is_idle(self):
        """True when the rider is idle and has no pending orders."""
        return self.state == RiderState.IDLE and not self.active_orders()

    def last_position(self):
        """Position where the rider will be after finishing all assigned orders."""
        active = self.active_orders()
        if active:
            return active[-1].cus_pos
        return self.position

    def estimate_workload(self):
        """Estimated remaining travel distance for all assigned orders."""
        active = self.active_orders()
        if not active:
            return 0
        total = PathPlanner.route_length([self.position] + list(self.route))
        pos = self.route[-1] if self.route else self.position
        for idx, order in enumerate(active):
            if idx == 0 and order is self._current_order:
                if self.state == RiderState.PICKING_UP:
                    total += order.distance
                pos = order.cus_pos
                continue
            total += PathPlanner.distance(pos, order.res_pos) + order.distance
            pos = order.cus_pos
        return total

    def _record(self, event, order_id):
        entry = {
            "time": _now(),
            "event": event,
            "order_id": order_id,
            "x": self.x,
            "y": self.y,
            "state": self.state,
        }
        self.log.append(entry)
        logger.debug("Rider %s: %s", self.rider_id, entry)
        return entry

    def _plan_to(self, target):
        points = PathPlanner.plan(self.position, target)
        self.special_case = PathPlanner.is_special_case(self.position, target)
        self.route = points[1:]

    def _advance(self, budget):
        """Move along the route using up to ``budget`` units. Returns leftover."""
        while budget > 0 and self.route:
            tx, ty = self.route[0]
            dist = abs(tx - self.x) + abs(ty - self.y)
            if dist <= budget:
                self.x, self.y = tx, ty
                budget -= dist
                self.distance_travelled += dist
                self.route.pop(0)
            else:
                if tx != self.x:
                    self.x += budget if tx > self.x else -budget
                else:
                    self.y += budget if ty > self.y else -budget
                self.distance_travelled += budget
                budget = 0
        return budget

    def _purge_completed(self):
        self.orders[:] = [o for o in self.orders
                          if getattr(o, "status", None) != STATUS_COMPLETED]

    def _coerce_orders(self):
        for idx, order in enumerate(self.orders):
            if not isinstance(order, Order) and not hasattr(order, "res_pos"):
                try:
                    if len(order) == 4:
                        new = Order((order[0], order[1]), (order[2], order[3]))
                        new.assign_to(self.rider_id)
                        self.orders[idx] = new
                except TypeError:
                    logger.warning("Rider %s: discarding invalid order %r",
                                   self.rider_id, order)
                    self.orders[idx] = None
        self.orders[:] = [o for o in self.orders if o is not None]

    def _start_order(self, order):
        self._current_order = order
        if getattr(order, "rider_id", None) is None:
            order.rider_id = self.rider_id
        if order.pickup_time is not None:
            self.state = int(RiderState.DELIVERING)
            order.status = STATUS_DELIVERING
            self._plan_to(order.cus_pos)
            return
        self.state = int(RiderState.PICKING_UP)
        order.status = STATUS_PICKING_UP
        if order.accept_time is None:
            order.accept_time = _now()
            self._record("accepted_order", order.id)
        self._plan_to(order.res_pos)

    def _finish_order(self, order):
        now = _now()
        order.complete(now)
        self._record("delivered_to_customer", order.id)
        if order in self.orders:
            self.orders.remove(order)
        self.completed_orders += 1
        self.state = int(RiderState.IDLE)
        self._current_order = None
        self.route = []
        self.special_case = False
        cfg = globalvar.get_value("config")
        revenue = 0
        if isinstance(cfg, dict):
            revenue = int(cfg.get("order_revenue", 0) or 0)
        if revenue:
            funds = int(globalvar.get_value("funds", 0) or 0)
            globalvar.set_value("funds", funds + revenue)

    # ------------------------------------------------------------------ public
    def move(self):
        """Advance the rider by one tick.

        Handles all state transitions (idle -> picking up -> delivering ->
        idle) and writes the corresponding log entries.
        """
        self._coerce_orders()
        self._purge_completed()
        if not self.orders:
            if self.state != RiderState.IDLE:
                self.state = int(RiderState.IDLE)
                self.route = []
                self._current_order = None
                self.special_case = False
            return

        order = self.orders[0]
        if self.state == RiderState.IDLE or self._current_order is not order:
            self._start_order(order)

        budget = self.speed
        for _ in range(10):
            target = order.res_pos if self.state == RiderState.PICKING_UP else order.cus_pos
            if not self.route and self.position != target:
                self._plan_to(target)
            budget = self._advance(budget)
            if self.route:
                break
            if self.state == RiderState.PICKING_UP:
                self.state = int(RiderState.DELIVERING)
                order.pickup_time = _now()
                order.status = STATUS_DELIVERING
                self._record("arrived_at_merchant", order.id)
                self._plan_to(order.cus_pos)
                continue
            self._finish_order(order)
            break

        self.x = GridMap.clamp(self.x)
        self.y = GridMap.clamp(self.y)

    def reset_route(self):
        """Recovery helper: drop the current route so it is re-planned."""
        self.route = []
        self.special_case = False

    def to_dict(self):
        """Serialise the rider."""
        return {
            "rider_id": self.rider_id,
            "x": self.x,
            "y": self.y,
            "speed": self.speed,
            "state": self.state,
            "orders": [getattr(o, "id", None) for o in self.orders],
            "special_case": self.special_case,
            "distance_travelled": self.distance_travelled,
            "completed_orders": self.completed_orders,
            "log": list(self.log),
        }

    def __repr__(self):
        return (f"Rider(id={self.rider_id}, pos=({self.x},{self.y}), "
                f"state={self.state}, orders={len(self.orders)})")
