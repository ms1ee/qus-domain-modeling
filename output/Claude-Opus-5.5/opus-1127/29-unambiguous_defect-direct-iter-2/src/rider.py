"""Rider model: movement, state machine and order handling."""

import logging

import globalvar
from path_planner import PathPlanner

logger = logging.getLogger(__name__)

IDLE = 0
PICKING_UP = 1
DELIVERING = 2

STATE_NAMES = {IDLE: "idle", PICKING_UP: "picking up",
               DELIVERING: "delivering"}

# Starting positions (all on road intersections).
SPAWN_POINTS = [(400, 400), (0, 0), (800, 0), (0, 800), (800, 800),
                (400, 0), (0, 400), (800, 400), (400, 800), (200, 200),
                (600, 600), (200, 600), (600, 200)]

DEFAULT_SPEED = 50


class Rider:
    """A delivery rider.

    Attributes:
        rider_id: unique id.
        x, y: current position.
        speed: units per tick.
        state: 0 idle, 1 picking up, 2 delivering.
        orders: assigned orders (first element is the active one).
        special_case: True while executing a special-case detour.
        log: list of event dicts (keys include "event" and "order_id").
    """

    def __init__(self, rider_id):
        self.rider_id = rider_id
        sx, sy = SPAWN_POINTS[(rider_id - 1) % len(SPAWN_POINTS)]
        self.x = sx
        self.y = sy
        config = globalvar.get_value("config") or {}
        try:
            self.speed = int(config.get("rider_speed", DEFAULT_SPEED))
        except (TypeError, ValueError):
            self.speed = DEFAULT_SPEED
        if self.speed <= 0:
            self.speed = DEFAULT_SPEED
        self.state = IDLE
        self.orders = []
        self.special_case = False
        self.path = []
        self.total_distance = 0
        self.completed_orders = 0
        self._plan_key = None
        self._planner = PathPlanner()
        self.log = []
        self._add_log("spawn", None)

    # ------------------------------------------------------------------ #
    def _now(self):
        return globalvar.get_value("time", 0)

    def _add_log(self, event, order_id):
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

    @property
    def state_name(self):
        """Human readable state."""
        return STATE_NAMES.get(self.state, "unknown")

    @property
    def position(self):
        """Current (x, y) position."""
        return (self.x, self.y)

    # ------------------------------------------------------------------ #
    def _ensure_plan(self, order):
        target = order.res_pos if self.state == PICKING_UP else order.cus_pos
        key = (order.id, self.state)
        if key != self._plan_key:
            self.path = self._planner.plan((self.x, self.y), target)
            self.special_case = self._planner.last_special
            self._plan_key = key

    def _advance(self, order):
        budget = self.speed
        moved = 0
        while budget > 0 and self.path:
            wx, wy = self.path[0]
            dx = wx - self.x
            dy = wy - self.y
            if dx != 0:
                step = min(budget, abs(dx))
                self.x += step if dx > 0 else -step
                budget -= step
                moved += step
            elif dy != 0:
                step = min(budget, abs(dy))
                self.y += step if dy > 0 else -step
                budget -= step
                moved += step
            if (self.x, self.y) == (wx, wy):
                self.path.pop(0)
        self.total_distance += moved
        if hasattr(order, "travel_distance"):
            order.travel_distance += moved
        if not self.path:
            self.special_case = False

    def move(self):
        """Advance the rider by one tick.

        Handles state transitions (idle -> picking up -> delivering ->
        idle) and records the corresponding log entries.
        """
        if self.state not in (IDLE, PICKING_UP, DELIVERING):
            self.state = IDLE
        if not self.orders:
            if self.state != IDLE:
                self.state = IDLE
            self.path = []
            self._plan_key = None
            self.special_case = False
            return
        order = self.orders[0]
        now = self._now()

        if self.state == IDLE:
            self.state = PICKING_UP
            if getattr(order, "rider_id", None) is None:
                order.assign_to(self.rider_id)
            order.accept_time = now
            self._add_log("accepted_order", order.id)

        self._ensure_plan(order)
        self._advance(order)

        if self.path:
            return

        if self.state == PICKING_UP:
            self.state = DELIVERING
            order.mark_picked_up(now)
            self._add_log("arrived_at_merchant", order.id)
            self._ensure_plan(order)
        elif self.state == DELIVERING:
            order.mark_completed(now)
            self.orders.pop(0)
            self.completed_orders += 1
            self.state = IDLE
            self.path = []
            self._plan_key = None
            self._add_log("delivered_to_customer", order.id)
            config = globalvar.get_value("config") or {}
            fee = config.get("delivery_fee", 0)
            funds = globalvar.get_value("funds")
            if funds is not None and fee:
                globalvar.set_value("funds", funds + fee)

    # ------------------------------------------------------------------ #
    def workload(self):
        """Estimate the final position and remaining distance of all
        currently assigned orders.

        Returns:
            (final_position, remaining_distance)
        """
        pos = (self.x, self.y)
        dist = 0
        for idx, o in enumerate(self.orders):
            if idx == 0 and self.state == DELIVERING:
                legs = [o.cus_pos]
            else:
                legs = [o.res_pos, o.cus_pos]
            for t in legs:
                pts = self._planner.plan(pos, t)
                dist += self._planner.path_length(pos, pts)
                pos = tuple(t)
        return pos, dist

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
            "total_distance": self.total_distance,
            "completed_orders": self.completed_orders,
            "log": list(self.log),
        }

    def __repr__(self):
        return (f"Rider(id={self.rider_id}, pos=({self.x},{self.y}), "
                f"state={self.state}, orders={len(self.orders)})")
