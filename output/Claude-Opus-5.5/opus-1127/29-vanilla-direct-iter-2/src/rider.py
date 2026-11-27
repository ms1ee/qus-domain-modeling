"""Rider model: movement, state machine and event log."""

import logging

import globalvar
from path_planner import PathPlanner

logger = logging.getLogger(__name__)

STATE_IDLE = 0
STATE_PICKING_UP = 1
STATE_DELIVERING = 2
STATE_NAMES = {0: "idle", 1: "picking up", 2: "delivering"}

DEFAULT_SPAWN = (435, 385)
DEFAULT_SPEED = 10


class Rider:
    """A delivery rider.

    Orders are assigned by appending them to ``rider.orders``; ``move()``
    advances the rider by one tick and performs all state transitions:
    idle(0) -> picking up(1) -> delivering(2) -> idle(0).
    """

    def __init__(self, rider_id):
        cfg = globalvar.get_value("config") or {}
        spawn = cfg.get("rider_spawn", DEFAULT_SPAWN)
        self.rider_id = rider_id
        self.x = int(spawn[0])
        self.y = int(spawn[1])
        self.speed = int(cfg.get("rider_speed", DEFAULT_SPEED))
        self.state = STATE_IDLE
        self.orders = []
        self.special_case = False
        self.log = []
        self.ticks = 0
        self.path = []
        self.target = None
        self.distance_travelled = 0
        self.delivered_count = 0
        self._log("spawn", None)

    # ------------------------------------------------------------------ utils
    def _time(self):
        t = globalvar.get_value("time")
        return t if isinstance(t, int) else self.ticks

    def _log(self, event, order_id):
        self.log.append({
            "time": self._time(),
            "event": event,
            "order_id": order_id,
            "x": self.x,
            "y": self.y,
            "state": self.state,
        })

    @property
    def position(self):
        """Current (x, y)."""
        return (self.x, self.y)

    @property
    def state_name(self):
        """Human readable state."""
        return STATE_NAMES.get(self.state, "unknown")

    def is_idle(self):
        """True when idle and without queued orders."""
        return self.state == STATE_IDLE and not self.orders

    def _set_target(self, pos):
        self.target = (int(pos[0]), int(pos[1]))
        self.path = PathPlanner.plan((self.x, self.y), self.target)
        # special case: directly above or below the target
        self.special_case = (self.x == self.target[0] and self.y != self.target[1])

    def _reset_idle(self):
        self.state = STATE_IDLE
        self.target = None
        self.path = []
        self.special_case = False

    def _advance(self, budget):
        """Move along the planned path using up to ``budget`` units."""
        while budget > 0 and self.path:
            wx, wy = self.path[0]
            if self.x != wx:
                step = min(budget, abs(wx - self.x))
                self.x += step if wx > self.x else -step
            elif self.y != wy:
                step = min(budget, abs(wy - self.y))
                self.y += step if wy > self.y else -step
            else:
                self.path.pop(0)
                continue
            budget -= step
            self.distance_travelled += step
            if (self.x, self.y) == (wx, wy):
                self.path.pop(0)
        return budget

    # ------------------------------------------------------------ transitions
    def _accept(self, order):
        self.state = STATE_PICKING_UP
        order.status = "picking_up"
        order.accepted_at = self._time()
        if getattr(order, "rider_id", None) is None:
            order.rider_id = self.rider_id
        self._log("accepted_order", order.id)
        self._set_target(order.res_pos)

    def _arrive_merchant(self, order):
        self.state = STATE_DELIVERING
        order.status = "delivering"
        order.picked_up_at = self._time()
        self._log("arrived_at_merchant", order.id)
        self._set_target(order.cus_pos)

    def _deliver(self, order):
        order.status = "completed"
        order.completed_at = self._time()
        if order in self.orders:
            self.orders.remove(order)
        self.delivered_count += 1
        self._reset_idle()
        self._log("delivered_to_customer", order.id)
        income = (globalvar.get_value("config") or {}).get("delivery_income", 0)
        funds = globalvar.get_value("funds")
        if income and isinstance(funds, int):
            globalvar.set_value("funds", funds + int(income))

    def move(self):
        """Advance the rider by one tick (movement + state transitions)."""
        self.ticks += 1
        if self.state != STATE_IDLE and not self.orders:
            logger.warning("Rider %s in state %s without orders; resetting",
                           self.rider_id, self.state)
            self._reset_idle()
            return
        if self.state == STATE_IDLE:
            if not self.orders:
                return
            self._accept(self.orders[0])
        elif self.target is None:
            order = self.orders[0]
            self._set_target(order.res_pos if self.state == STATE_PICKING_UP
                             else order.cus_pos)

        budget = self.speed
        for _ in range(10):
            budget = self._advance(budget)
            if (self.x, self.y) != self.target:
                if not self.path:
                    # watchdog: replan when stuck without a path
                    self._set_target(self.target)
                break
            order = self.orders[0]
            if self.state == STATE_PICKING_UP:
                self._arrive_merchant(order)
            else:
                self._deliver(order)
                break

    def remaining_route_points(self):
        """Points the rider still has to visit (current pos first)."""
        points = [(self.x, self.y)]
        for i, order in enumerate(self.orders):
            if i == 0 and self.state == STATE_DELIVERING:
                points.append(order.cus_pos)
            else:
                points.append(order.res_pos)
                points.append(order.cus_pos)
        return points

    def to_dict(self):
        """JSON-serialisable representation."""
        return {
            "rider_id": self.rider_id,
            "x": self.x,
            "y": self.y,
            "speed": self.speed,
            "state": self.state,
            "orders": [o.id for o in self.orders],
            "special_case": self.special_case,
            "distance_travelled": self.distance_travelled,
            "delivered_count": self.delivered_count,
            "log": list(self.log),
        }

    def __repr__(self):
        return "Rider(id=%s, pos=(%s,%s), state=%s, orders=%d)" % (
            self.rider_id, self.x, self.y, self.state, len(self.orders))
