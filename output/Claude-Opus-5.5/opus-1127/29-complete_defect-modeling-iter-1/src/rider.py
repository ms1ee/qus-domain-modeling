"""Rider model: movement, state machine and status log."""

import logging
from enum import IntEnum

import globalvar
from grid_map import clamp_coord
from path_planner import PathPlanner, manhattan

logger = logging.getLogger("dispatch.rider")


class RiderState(IntEnum):
    """Rider state enumeration."""
    IDLE = 0
    PICKING_UP = 1
    DELIVERING = 2


STATE_NAMES = {0: "idle", 1: "picking up", 2: "delivering"}


class Rider:
    """A delivery rider.

    Orders are assigned by appending them to ``rider.orders``.  Each call to
    :meth:`move` advances the rider by one tick; state transitions and log
    entries happen there.
    """

    def __init__(self, rider_id, x=None, y=None, speed=None):
        start = globalvar.get_value("rider_start", (400, 400))
        self.rider_id = rider_id
        self.x = clamp_coord(start[0] if x is None else x)
        self.y = clamp_coord(start[1] if y is None else y)
        self.speed = int(speed if speed is not None
                         else globalvar.get_value("rider_speed", 50))
        if self.speed <= 0:
            self.speed = 50
        self.state = RiderState.IDLE
        self.orders = []
        self.special_case = False
        self.log = []
        self.current_order = None
        self.path = []
        self.current_route = None
        self.completed_orders = []
        self.distance_travelled = 0
        self._planner = PathPlanner()
        self._log("spawn", None)

    # ------------------------------------------------------------------ helpers
    def _now(self):
        return globalvar.get_value("time", 0)

    def _log(self, event, order):
        """Append a status record to the rider log."""
        self.log.append({
            "time": self._now(),
            "event": event,
            "order_id": getattr(order, "id", None) if order is not None else None,
            "x": self.x,
            "y": self.y,
            "state": int(self.state),
        })
        limit = globalvar.get_value("max_log_entries", 5000)
        if limit and len(self.log) > limit:
            del self.log[:len(self.log) - limit]
        logger.debug("Rider %s %s order=%s at (%d,%d)", self.rider_id, event,
                     self.log[-1]["order_id"], self.x, self.y)

    def pending_orders(self):
        """Orders assigned to this rider that are not completed."""
        return [o for o in self.orders if getattr(o, "status", "") != "completed"]

    def _set_route(self, goal):
        route = self._planner.plan((self.x, self.y), goal)
        self.current_route = route
        self.path = list(route.points[1:])
        self.special_case = route.special_case

    def _advance(self, budget):
        """Move along ``self.path`` using up to ``budget`` units."""
        while budget > 0 and self.path:
            tx, ty = self.path[0]
            dx, dy = tx - self.x, ty - self.y
            dist = abs(dx) + abs(dy)
            if dist == 0:
                self.path.pop(0)
                continue
            if dist <= budget:
                self.x, self.y = tx, ty
                budget -= dist
                self.distance_travelled += dist
                self.path.pop(0)
            else:
                step = budget
                if dx:
                    s = min(step, abs(dx))
                    self.x += s if dx > 0 else -s
                    step -= s
                if step and dy:
                    s = min(step, abs(dy))
                    self.y += s if dy > 0 else -s
                self.distance_travelled += budget
                budget = 0

    def _at(self, pos):
        return not self.path and (self.x, self.y) == (int(pos[0]), int(pos[1]))

    # --------------------------------------------------------------- simulation
    def move(self):
        """Advance the rider by one tick."""
        if self.state != RiderState.IDLE and (
                self.current_order is None
                or self.current_order.status == "completed"):
            self.reset()
        if self.state == RiderState.IDLE:
            pending = self.pending_orders()
            if not pending:
                return
            order = pending[0]
            self.current_order = order
            self.state = RiderState.PICKING_UP
            order.status = "picking_up"
            if getattr(order, "rider_id", None) is None:
                order.rider_id = self.rider_id
            order.accept_time = self._now()
            self._log("accepted_order", order)
            self._set_route(order.res_pos)

        self._advance(self.speed)
        order = self.current_order
        if self.state == RiderState.PICKING_UP and self._at(order.res_pos):
            self.state = RiderState.DELIVERING
            order.status = "delivering"
            order.pickup_time = self._now()
            self._log("arrived_at_merchant", order)
            self._set_route(order.cus_pos)
        elif self.state == RiderState.DELIVERING and self._at(order.cus_pos):
            self._complete(order)

    def _complete(self, order):
        now = self._now()
        order.status = "completed"
        order.completion_time = now
        start = getattr(order, "start_time", None)
        order.time_taken = now - start if start is not None else None
        self.state = RiderState.IDLE
        self._log("delivered_to_customer", order)
        if order in self.orders:
            self.orders.remove(order)
        self.completed_orders.append(order.id)
        if len(self.completed_orders) > 10000:
            del self.completed_orders[:-10000]
        self.current_order = None
        self.path = []
        self.current_route = None
        self.special_case = False
        funds = globalvar.get_value("funds")
        if funds is not None:
            globalvar.set_value("funds", funds + int(getattr(order, "fee", 0)))

    def reset(self):
        """Recover to a consistent idle state (used for error recovery)."""
        self.state = RiderState.IDLE
        self.current_order = None
        self.path = []
        self.current_route = None
        self.special_case = False
        self.x = clamp_coord(self.x)
        self.y = clamp_coord(self.y)

    # ---------------------------------------------------------------- estimates
    def remaining_route_distance(self):
        """Distance left on the current path."""
        pos = (self.x, self.y)
        dist = 0
        for p in self.path:
            dist += manhattan(pos, p)
            pos = p
        return dist

    def estimate_workload(self):
        """Return ``(remaining_distance, final_position)`` for queued work."""
        pos = (self.x, self.y)
        dist = 0
        cur = self.current_order
        if cur is not None and cur.status != "completed":
            if self.state == RiderState.PICKING_UP:
                dist += self.remaining_route_distance()
                pos = tuple(cur.res_pos)
                dist += manhattan(pos, cur.cus_pos)
                pos = tuple(cur.cus_pos)
            elif self.state == RiderState.DELIVERING:
                dist += self.remaining_route_distance()
                pos = tuple(cur.cus_pos)
        for o in self.pending_orders():
            if o is cur:
                continue
            dist += manhattan(pos, o.res_pos) + manhattan(o.res_pos, o.cus_pos)
            pos = tuple(o.cus_pos)
        return dist, pos

    @property
    def state_name(self):
        return STATE_NAMES.get(int(self.state), "unknown")

    def to_dict(self):
        """Serializable representation."""
        return {
            "rider_id": self.rider_id,
            "x": self.x,
            "y": self.y,
            "speed": self.speed,
            "state": int(self.state),
            "orders": [o.id for o in self.orders],
            "special_case": self.special_case,
            "completed_orders": list(self.completed_orders),
            "distance_travelled": self.distance_travelled,
            "log": list(self.log),
        }

    def __repr__(self):
        return "Rider(id=%s, pos=(%d,%d), state=%s)" % (
            self.rider_id, self.x, self.y, self.state_name)
