"""Rider model: movement, state machine and event log."""

import logging

import globalvar
from path_planner import PathPlanner

logger = logging.getLogger(__name__)

STATE_IDLE = 0
STATE_PICKING_UP = 1
STATE_DELIVERING = 2

STATE_NAMES = {
    STATE_IDLE: "idle",
    STATE_PICKING_UP: "picking up",
    STATE_DELIVERING: "delivering",
}

DEFAULT_START = (400, 400)
DEFAULT_SPEED = 100


class Rider:
    """A delivery rider.

    Orders are assigned by appending ``Order`` objects to ``rider.orders``.
    Each call to :meth:`move` advances the rider by one tick.
    """

    def __init__(self, rider_id, x=None, y=None, speed=None):
        cfg = globalvar.get_value("config", {}) or {}
        start = cfg.get("rider_start", DEFAULT_START)
        self.rider_id = rider_id
        self.x = int(start[0] if x is None else x)
        self.y = int(start[1] if y is None else y)
        if speed is None:
            speed = globalvar.get_value("rider_speed", DEFAULT_SPEED)
        self.speed = max(1, int(speed))
        self.state = STATE_IDLE
        self.orders = []
        self.special_case = False
        self.path = []
        self.current_order = None
        self.log = []
        self.total_distance = 0
        self.completed_orders = 0
        self._log("spawn", None)

    # ------------------------------------------------------------------ log
    def _log(self, event, order_id):
        entry = {
            "time": globalvar.get_value("time", 0),
            "rider_id": self.rider_id,
            "event": event,
            "order_id": order_id,
            "x": self.x,
            "y": self.y,
            "state": self.state,
        }
        self.log.append(entry)
        logger.debug("rider %s: %s", self.rider_id, entry)

    # ------------------------------------------------------------ properties
    @property
    def position(self):
        return (self.x, self.y)

    @property
    def state_name(self):
        return STATE_NAMES.get(self.state, "unknown")

    # -------------------------------------------------------------- movement
    def _set_path_to(self, target):
        self.special_case = PathPlanner.is_vertically_aligned(
            self.position, target)
        self.path = PathPlanner.plan(self.position, target)

    def _advance(self):
        """Move up to ``speed`` units along the current path."""
        remaining = self.speed
        while remaining > 0 and self.path:
            tx, ty = self.path[0]
            dx, dy = tx - self.x, ty - self.y
            dist = abs(dx) + abs(dy)
            if dist <= remaining:
                self.x, self.y = tx, ty
                remaining -= dist
                self.total_distance += dist
                self.path.pop(0)
                continue
            if dx != 0:
                step = min(remaining, abs(dx))
                self.x += step if dx > 0 else -step
            else:
                step = min(remaining, abs(dy))
                self.y += step if dy > 0 else -step
            remaining -= step
            self.total_distance += step

    def move(self):
        """Advance one tick, performing state transitions and logging."""
        try:
            self._move()
        except Exception:  # error recovery: keep the simulation alive
            logger.exception("rider %s failed to move; recovering",
                             self.rider_id)
            self._recover()

    def _recover(self):
        if self.current_order is not None and \
                self.current_order not in self.orders:
            self.current_order = None
        if self.current_order is None:
            self.state = STATE_IDLE
            self.path = []

    def _move(self):
        if self.state == STATE_IDLE:
            if not self.orders:
                return
            order = self.orders[0]
            self.current_order = order
            if hasattr(order, "mark_accepted"):
                order.mark_accepted(self.rider_id)
            self.state = STATE_PICKING_UP
            self._set_path_to(order.res_pos)
            self._log("accepted_order", order.id)
            return

        order = self.current_order
        if order is None:
            # inconsistent state: recover to idle
            self.state = STATE_IDLE
            self.path = []
            return

        self._advance()
        if self.path:
            return

        if self.state == STATE_PICKING_UP:
            if hasattr(order, "mark_picked_up"):
                order.mark_picked_up()
            self.state = STATE_DELIVERING
            self._log("arrived_at_merchant", order.id)
            self._set_path_to(order.cus_pos)
        elif self.state == STATE_DELIVERING:
            self._complete(order)

    def _complete(self, order):
        now = globalvar.get_value("time", 0)
        if hasattr(order, "mark_completed"):
            order.mark_completed(now)
        else:
            order.status = "completed"
        fee = getattr(order, "fee", 0)
        globalvar.set_value("funds", globalvar.get_value("funds", 0) + fee)
        if order in self.orders:
            self.orders.remove(order)
        self.current_order = None
        self.path = []
        self.special_case = False
        self.state = STATE_IDLE
        self.completed_orders += 1
        self._log("delivered_to_customer", order.id)

    # ------------------------------------------------------------- planning
    def full_route(self):
        """All remaining waypoints (starting at current position)."""
        pos = self.position
        pts = [pos]
        if self.state != STATE_IDLE and self.current_order is not None:
            pts.extend(self.path)
            if self.path:
                pos = self.path[-1]
            if self.state == STATE_PICKING_UP:
                seg = PathPlanner.plan(pos, self.current_order.cus_pos)
                pts.extend(seg)
                pos = self.current_order.cus_pos
            queued = [o for o in self.orders if o is not self.current_order]
        else:
            queued = list(self.orders)
        for o in queued:
            pts.extend(PathPlanner.plan(pos, o.res_pos))
            pts.extend(PathPlanner.plan(o.res_pos, o.cus_pos))
            pos = o.cus_pos
        return pts

    def workload(self):
        """Return (remaining distance, end position) of queued work."""
        pts = self.full_route()
        return PathPlanner.route_length(pts[0], pts[1:]), pts[-1]

    def estimate_cost(self, target):
        """Distance this rider must cover before reaching ``target``."""
        dist, end = self.workload()
        return dist + PathPlanner.path_length(end, target)

    def to_dict(self):
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
        return "Rider(id=%s, pos=(%s,%s), state=%s, orders=%s)" % (
            self.rider_id, self.x, self.y, self.state,
            [o.id for o in self.orders])
