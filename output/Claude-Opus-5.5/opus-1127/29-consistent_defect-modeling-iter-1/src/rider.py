"""Rider model: movement, state machine and status-change log."""

import globalvar
from path_planner import PathPlanner

IDLE = 0
PICKING_UP = 1
DELIVERING = 2

STATE_NAMES = {IDLE: "idle", PICKING_UP: "picking up", DELIVERING: "delivering"}

DEFAULT_SPEED = 20
START_X = 400
START_Y = 400


class Rider:
    """A delivery rider.

    Orders are assigned by appending them to ``rider.orders``; each call to
    :meth:`move` advances the rider by one tick.
    """

    def __init__(self, rider_id, x=START_X, y=START_Y, speed=None):
        self.rider_id = rider_id
        self.x = int(x)
        self.y = int(y)
        if speed is None:
            speed = globalvar.get_value("rider_speed") or DEFAULT_SPEED
        self.speed = int(speed)
        self.state = IDLE
        self.orders = []
        self.special_case = False
        self.current_order = None
        self.path = []
        self._path_target = None
        self.planner = PathPlanner()
        self.total_distance = 0
        self.log = []
        self._record("spawn", None, None, IDLE)

    # ------------------------------------------------------------------ helpers
    @staticmethod
    def _now():
        tick = globalvar.get_value("tick")
        return tick if isinstance(tick, int) else 0

    def _record(self, event, order, from_state, to_state):
        self.log.append({
            "event": event,
            "order_id": getattr(order, "id", None) if order is not None else None,
            "time": self._now(),
            "x": self.x,
            "y": self.y,
            "from_state": from_state,
            "to_state": to_state,
        })

    @property
    def state_name(self):
        """Human readable state."""
        return STATE_NAMES.get(self.state, str(self.state))

    def pending_orders(self):
        """Orders assigned but not yet started."""
        return [o for o in self.orders
                if getattr(o, "status", "pending") != "completed"
                and o is not self.current_order]

    def active_order_count(self):
        """Number of uncompleted orders held by this rider."""
        return sum(1 for o in self.orders
                   if getattr(o, "status", "pending") != "completed")

    def is_idle(self):
        """True if the rider has no work at all."""
        return self.state == IDLE and self.active_order_count() == 0

    # ---------------------------------------------------------------- movement
    def _accept_next(self):
        pending = self.pending_orders()
        if not pending:
            self.current_order = None
            return False
        order = pending[0]
        if getattr(order, "rider_id", None) is None and hasattr(order, "assign_to"):
            order.assign_to(self.rider_id)
        self.current_order = order
        old = self.state
        self.state = PICKING_UP
        if hasattr(order, "mark_accepted"):
            order.mark_accepted(self._now())
        self._path_target = None
        self._record("accepted_order", order, old, PICKING_UP)
        return True

    def _advance_towards(self, tx, ty, budget):
        """Move up to ``budget`` units along a planned path to (tx, ty)."""
        if (self.x, self.y) == (tx, ty):
            return budget
        if self._path_target != (tx, ty) or not self.path:
            self.special_case = self.x == tx and self.y != ty
            self.path = self.planner.plan((self.x, self.y), (tx, ty)).waypoints[1:]
            self._path_target = (tx, ty)
        while budget > 0 and self.path:
            wx, wy = self.path[0]
            dist = abs(wx - self.x) + abs(wy - self.y)
            if dist <= budget:
                self.x, self.y = wx, wy
                budget -= dist
                self.total_distance += dist
                self.path.pop(0)
            else:
                if wx != self.x:
                    self.x += budget if wx > self.x else -budget
                else:
                    self.y += budget if wy > self.y else -budget
                self.total_distance += budget
                budget = 0
        return budget

    def move(self):
        """Advance the rider by one tick, performing state transitions."""
        budget = self.speed
        if self.state == IDLE or self.current_order is None:
            if not self._accept_next():
                self.state = IDLE
                return
        while self.current_order is not None:
            order = self.current_order
            if self.state == PICKING_UP:
                target = (order.res_x, order.res_y)
                budget = self._advance_towards(target[0], target[1], budget)
                if (self.x, self.y) == target:
                    self.state = DELIVERING
                    if hasattr(order, "mark_picked_up"):
                        order.mark_picked_up(self._now())
                    self._path_target = None
                    self._record("arrived_at_merchant", order, PICKING_UP, DELIVERING)
                    continue
                break
            if self.state == DELIVERING:
                target = (order.cus_x, order.cus_y)
                budget = self._advance_towards(target[0], target[1], budget)
                if (self.x, self.y) == target:
                    if hasattr(order, "mark_completed"):
                        order.mark_completed(self._now())
                    else:
                        order.status = "completed"
                    self.state = IDLE
                    self.current_order = None
                    self.special_case = False
                    self._path_target = None
                    self._record("delivered_to_customer", order, DELIVERING, IDLE)
                    if budget > 0 and self._accept_next():
                        continue
                    if budget == 0 and self.pending_orders():
                        self._accept_next()
                    break
                break
            break

    def remaining_stops(self):
        """Ordered list of stops still to visit."""
        stops = []
        order = self.current_order
        if order is not None:
            if self.state == PICKING_UP:
                stops.append((order.res_x, order.res_y))
            stops.append((order.cus_x, order.cus_y))
        for o in self.pending_orders():
            stops.append((o.res_x, o.res_y))
            stops.append((o.cus_x, o.cus_y))
        return stops

    def to_dict(self):
        """Serialisable representation."""
        return {
            "rider_id": self.rider_id,
            "x": self.x,
            "y": self.y,
            "speed": self.speed,
            "state": self.state,
            "special_case": self.special_case,
            "orders": [getattr(o, "id", None) for o in self.orders],
            "total_distance": self.total_distance,
            "log": list(self.log),
        }

    def __repr__(self):
        return "Rider(id=%s, pos=(%d,%d), state=%s, orders=%d)" % (
            self.rider_id, self.x, self.y, self.state_name, len(self.orders))
