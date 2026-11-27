"""Rider model: movement, state and orders."""

import globalvar
from config import DEFAULT_CONFIG
from path_planner import PathPlanner

IDLE = 0
PICKING_UP = 1
DELIVERING = 2

STATE_NAMES = {IDLE: "idle", PICKING_UP: "picking up", DELIVERING: "delivering"}


class RiderState:
    """Rider state enumeration."""
    IDLE = IDLE
    PICKING_UP = PICKING_UP
    DELIVERING = DELIVERING


class Rider:
    """A delivery rider.

    Orders are assigned by appending them to ``rider.orders``; the rider
    handles them sequentially in ``move()``.
    """

    def __init__(self, rider_id):
        cfg = globalvar.get_value("config") or DEFAULT_CONFIG
        self.rider_id = rider_id
        self.x = int(cfg.get("initial_rider_x", 435))
        self.y = int(cfg.get("initial_rider_y", 385))
        self.speed = int(cfg.get("rider_speed", 10))
        self.state = IDLE
        self.orders = []
        self.special_case = False
        self.distance_travelled = 0
        self.log = []
        self._record("spawn", None)

    # ------------------------------------------------------------------
    def _record(self, event, order_id):
        self.log.append({
            "time": globalvar.get_value("tick", 0),
            "x": self.x,
            "y": self.y,
            "event": event,
            "order_id": order_id,
            "state": self.state,
        })

    @property
    def position(self):
        """Current (x, y) position."""
        return (self.x, self.y)

    @property
    def state_name(self):
        """Human readable state."""
        return STATE_NAMES.get(self.state, "unknown")

    def is_idle(self):
        """True if the rider has no work."""
        return self.state == IDLE and not self.orders

    # ------------------------------------------------------------------
    def _advance(self, target, order):
        """Move up to ``speed`` units towards ``target`` along streets."""
        remaining = self.speed
        target = (int(target[0]), int(target[1]))
        guard = 0
        while remaining > 0 and (self.x, self.y) != target and guard < 16:
            guard += 1
            pos = (self.x, self.y)
            self.special_case = PathPlanner.is_vertical_special(pos, target)
            route = PathPlanner.plan_route(pos, target)
            if not route:
                break
            wx, wy = route[0]
            dist = abs(wx - self.x) + abs(wy - self.y)
            if dist == 0:
                break
            step = min(remaining, dist)
            if wx != self.x:
                self.x += step if wx > self.x else -step
            else:
                self.y += step if wy > self.y else -step
            remaining -= step
            self.distance_travelled += step
            if order is not None:
                order.travel_distance += step

    def move(self):
        """Advance the rider by one tick.

        Handles state transitions (idle -> picking up -> delivering -> idle)
        and records the corresponding log entries.
        """
        if not self.orders:
            if self.state != IDLE:
                self.state = IDLE
            self.special_case = False
            return
        order = self.orders[0]
        tick = globalvar.get_value("tick", 0)
        if self.state == IDLE:
            self.state = PICKING_UP
            if getattr(order, "rider_id", None) is None:
                order.rider_id = self.rider_id
            order.status = "picking_up"
            if getattr(order, "assign_time", None) is None:
                order.assign_time = tick
            self._record("accepted_order", order.id)

        target = order.res_pos if self.state == PICKING_UP else order.cus_pos
        self._advance(target, order)

        if (self.x, self.y) == (int(target[0]), int(target[1])):
            if self.state == PICKING_UP:
                self.state = DELIVERING
                order.status = "delivering"
                order.pickup_time = tick
                self._record("arrived_at_merchant", order.id)
            elif self.state == DELIVERING:
                order.status = "completed"
                order.completion_time = tick
                start = order.start_time if order.start_time is not None else 0
                order.time_taken = tick - start
                self.orders.pop(0)
                self.state = IDLE
                self.special_case = False
                self._record("delivered_to_customer", order.id)

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
            "distance_travelled": self.distance_travelled,
            "log": list(self.log),
        }

    def __repr__(self):
        return "Rider(id=%s, pos=(%d,%d), state=%d, orders=%d)" % (
            self.rider_id, self.x, self.y, self.state, len(self.orders))
