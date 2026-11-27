"""Rider model: movement, state machine and status log."""

import logging
from enum import IntEnum

import globalvar
from path_planner import PathPlanner

logger = logging.getLogger(__name__)

DEFAULT_SPEED = 20
START_POSITION = (400, 400)


class RiderState(IntEnum):
    """Rider status enumeration."""
    IDLE = 0
    PICKING_UP = 1
    DELIVERING = 2


STATE_NAMES = {
    RiderState.IDLE: "idle",
    RiderState.PICKING_UP: "picking up",
    RiderState.DELIVERING: "delivering",
}


class Rider:
    """A delivery rider.

    Orders are assigned by appending them to ``rider.orders``. Each call to
    :meth:`move` advances the rider by one tick.
    """

    def __init__(self, rider_id, x=START_POSITION[0], y=START_POSITION[1],
                 speed=None):
        self.rider_id = rider_id
        self.x = int(x)
        self.y = int(y)
        if speed is None:
            speed = globalvar.get_value("rider_speed", DEFAULT_SPEED) or DEFAULT_SPEED
        self.speed = int(speed)
        self.state = RiderState.IDLE
        self.orders = []
        self.special_case = False
        self.current_order = None
        self.path = []
        self.log = []
        self.distance_travelled = 0
        self._planner = PathPlanner()
        self._record("spawn", None)

    # ---------------------------------------------------------------- helpers
    @property
    def id(self):
        return self.rider_id

    @property
    def position(self):
        return (self.x, self.y)

    @property
    def state_name(self):
        return STATE_NAMES.get(RiderState(self.state), str(self.state))

    @property
    def active_orders(self):
        return [o for o in self.orders if o.status != "completed"]

    @property
    def active_order_count(self):
        return len(self.active_orders)

    def is_idle(self):
        return self.state == RiderState.IDLE and self.active_order_count == 0

    def _tick(self):
        return globalvar.get_value("tick", 0) or 0

    def _record(self, event, order_id):
        self.log.append({
            "time": self._tick(), "event": event, "order_id": order_id,
            "x": self.x, "y": self.y, "state": int(self.state),
        })
        logger.debug("Rider %s: %s (order %s) at (%s,%s)",
                     self.rider_id, event, order_id, self.x, self.y)

    def _next_pending_order(self):
        for o in self.orders:
            if o.status != "completed" and o is not self.current_order:
                return o
        return None

    def _plan_to(self, target):
        self.special_case = PathPlanner.is_special_case(
            self.x, self.y, target[0], target[1])
        self.path = self._planner.plan(self.x, self.y, target[0], target[1])

    # ------------------------------------------------------------ transitions
    def _accept(self, order):
        if order.rider_id != self.rider_id:
            order.assign_to(self.rider_id)
        self.current_order = order
        self.state = RiderState.PICKING_UP
        order.status = "picking_up"
        self._plan_to(order.res_pos)
        self._record("accepted_order", order.id)

    def _arrive(self):
        order = self.current_order
        if order is None:
            return
        if self.state == RiderState.PICKING_UP:
            self.state = RiderState.DELIVERING
            order.status = "delivering"
            order.pickup_time = self._tick()
            self._record("arrived_at_merchant", order.id)
            self._plan_to(order.cus_pos)
        elif self.state == RiderState.DELIVERING:
            self._complete()
        else:
            # Inconsistent state: restart the pickup leg.
            self.state = RiderState.PICKING_UP
            self._plan_to(order.res_pos)

    def _complete(self):
        order = self.current_order
        order.mark_completed(self._tick())
        self._record("delivered_to_customer", order.id)
        self.current_order = None
        self.path = []
        nxt = self._next_pending_order()
        if nxt is not None:
            self._accept(nxt)
        else:
            self.state = RiderState.IDLE
            self.special_case = False

    # --------------------------------------------------------------- movement
    def move(self):
        """Advance the rider by one tick."""
        if self.current_order is not None and self.current_order.status == "completed":
            self.current_order = None
            self.path = []
        if self.current_order is None:
            nxt = self._next_pending_order()
            if nxt is None:
                self.state = RiderState.IDLE
                return
            self._accept(nxt)
        budget = self.speed
        while budget > 0 and self.path:
            tx, ty = self.path[0]
            dx, dy = tx - self.x, ty - self.y
            if dx:
                step = min(abs(dx), budget)
                self.x += step if dx > 0 else -step
            elif dy:
                step = min(abs(dy), budget)
                self.y += step if dy > 0 else -step
            else:
                step = 0
            budget -= step
            self.distance_travelled += step
            if (self.x, self.y) == (tx, ty):
                self.path.pop(0)
        if not self.path:
            self._arrive()

    def remaining_route(self):
        """Return (points, length) of the full remaining planned route."""
        pos = (self.x, self.y)
        points = list(self.path)
        end = points[-1] if points else pos
        targets = []
        if self.current_order is not None and self.state == RiderState.PICKING_UP:
            targets.append(self.current_order.cus_pos)
        for o in self.orders:
            if o.status != "completed" and o is not self.current_order:
                targets.extend([o.res_pos, o.cus_pos])
        more, _ = self._planner.plan_multi(end, targets)
        points.extend(more)
        return points, self._planner.path_length(pos, points)

    # ------------------------------------------------------------ persistence
    def to_dict(self):
        return {
            "rider_id": self.rider_id, "x": self.x, "y": self.y,
            "speed": self.speed, "state": int(self.state),
            "special_case": self.special_case,
            "orders": [o.id for o in self.orders],
            "current_order": self.current_order.id if self.current_order else None,
            "path": [list(p) for p in self.path],
            "log": self.log, "distance_travelled": self.distance_travelled,
        }

    @classmethod
    def from_dict(cls, data, orders_by_id):
        obj = cls.__new__(cls)
        obj.rider_id = data["rider_id"]
        obj.x, obj.y = int(data["x"]), int(data["y"])
        obj.speed = int(data.get("speed", DEFAULT_SPEED))
        obj.state = RiderState(int(data.get("state", 0)))
        obj.special_case = bool(data.get("special_case", False))
        obj.orders = [orders_by_id[i] for i in data.get("orders", [])
                      if i in orders_by_id]
        cur = data.get("current_order")
        obj.current_order = orders_by_id.get(cur) if cur is not None else None
        obj.path = [tuple(p) for p in data.get("path", [])]
        obj.log = list(data.get("log", []))
        obj.distance_travelled = data.get("distance_travelled", 0)
        obj._planner = PathPlanner()
        return obj

    def __repr__(self):
        return (f"Rider(id={self.rider_id}, pos=({self.x},{self.y}), "
                f"state={self.state_name}, orders={len(self.orders)})")


def recruit_rider(cost=None):
    """Create a new rider, deduct the recruitment cost and register it."""
    riders = globalvar.get_value("riders")
    if riders is None:
        riders = []
        globalvar.set_value("riders", riders)
    counter = globalvar.get_value("rider_id", 0) or 0
    existing = max([r.rider_id for r in riders], default=0)
    new_id = max(counter, existing) + 1
    globalvar.set_value("rider_id", new_id)
    if cost is None:
        cost = globalvar.get_value("recruitment_cost", 500)
        if cost is None:
            cost = 500
    globalvar.set_value("funds", (globalvar.get_value("funds", 0) or 0) - cost)
    rider = Rider(new_id)
    riders.append(rider)
    logger.info("Recruited rider %s (cost %s)", new_id, cost)
    return rider
