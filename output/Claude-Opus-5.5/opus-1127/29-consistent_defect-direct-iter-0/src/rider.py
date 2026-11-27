"""Rider model: movement, state machine and event log."""

import logging

import globalvar
from config import RIDER_SPEED, RIDER_START
from order_model import (Order, STATUS_COMPLETED, STATUS_DELIVERING,
                         STATUS_PICKING_UP)
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


def _status_of(order):
    return getattr(order, "status", None)


class Rider:
    """A delivery rider.

    Orders are assigned by appending them to ``rider.orders``. Each call to
    :meth:`move` advances the rider by one tick; state transitions and log
    entries happen there.
    """

    def __init__(self, rider_id, x=None, y=None, speed=None):
        self.rider_id = rider_id
        self.x = int(RIDER_START[0] if x is None else x)
        self.y = int(RIDER_START[1] if y is None else y)
        self.speed = int(RIDER_SPEED if speed is None else speed)
        if self.speed < 1:
            self.speed = 1
        self.state = STATE_IDLE
        self.orders = []
        self.special_case = False
        self.log = []
        self.current_order = None
        self.path = []
        self.ticks = 0
        self.total_distance = 0
        self._record("spawn", None)

    # ------------------------------------------------------------------ utils
    def _now(self):
        t = globalvar.get_value("time")
        return t if isinstance(t, int) else self.ticks

    def _record(self, event, order_id):
        self.log.append({
            "event": event,
            "order_id": order_id,
            "time": self._now(),
            "x": self.x,
            "y": self.y,
            "state": self.state,
        })

    @property
    def position(self):
        """Current (x, y) position."""
        return (self.x, self.y)

    @property
    def state_name(self):
        """Human-readable state."""
        return STATE_NAMES.get(self.state, str(self.state))

    def active_orders(self):
        """Orders not yet completed."""
        return [o for o in self.orders if _status_of(o) != STATUS_COMPLETED]

    def active_order_count(self):
        """Number of orders not yet completed."""
        return len(self.active_orders())

    def is_idle(self):
        """True if the rider is idle with no outstanding orders."""
        return self.state == STATE_IDLE and self.active_order_count() == 0

    def _normalize_orders(self):
        """Convert raw ``[rx, ry, cx, cy]`` entries into Order objects."""
        for i, o in enumerate(self.orders):
            if isinstance(o, (list, tuple)) and len(o) == 4:
                order = Order((o[0], o[1]), (o[2], o[3]))
                order.assign_to(self.rider_id)
                self.orders[i] = order

    def _current_target(self):
        order = self.current_order
        if self.state == STATE_PICKING_UP:
            return tuple(order.res_pos)
        return tuple(order.cus_pos)

    def _replan(self):
        target = self._current_target()
        self.special_case = PathPlanner.is_special_case(self.position, target)
        self.path = PathPlanner.plan(self.position, target)

    def _accept_next(self):
        """Take the next outstanding order. Returns True if one was taken."""
        for order in self.orders:
            if _status_of(order) == STATUS_COMPLETED:
                continue
            self.current_order = order
            if getattr(order, "rider_id", None) is None and \
                    hasattr(order, "assign_to"):
                order.assign_to(self.rider_id)
            if _status_of(order) == STATUS_DELIVERING:
                self.state = STATE_DELIVERING
            else:
                self.state = STATE_PICKING_UP
                order.status = STATUS_PICKING_UP
                order.accepted_time = self._now()
                self._record("accepted_order", order.id)
            self._replan()
            return True
        self.current_order = None
        return False

    def _arrive(self):
        order = self.current_order
        if self.state == STATE_PICKING_UP:
            self.state = STATE_DELIVERING
            order.status = STATUS_DELIVERING
            order.pickup_time = self._now()
            self._record("arrived_at_merchant", order.id)
            self._replan()
        else:
            order.status = STATUS_COMPLETED
            order.completed_time = self._now()
            self._record("delivered_to_customer", order.id)
            self.current_order = None
            self.path = []
            self.special_case = False
            if not self._accept_next():
                self.state = STATE_IDLE

    # ---------------------------------------------------------------- moving
    def move(self):
        """Advance the rider by one tick. Returns the resulting state."""
        self.ticks += 1
        self._normalize_orders()
        if self.current_order is None or \
                _status_of(self.current_order) == STATUS_COMPLETED or \
                self.current_order not in self.orders:
            self.current_order = None
            if not self._accept_next():
                self.state = STATE_IDLE
                return self.state
        budget = self.speed
        guard = 0
        while self.current_order is not None and guard < 1000:
            guard += 1
            target = self._current_target()
            if self.position == target:
                self._arrive()
                continue
            if budget <= 0:
                break
            if not self.path or tuple(self.path[-1]) != target:
                self._replan()
            new_pos, self.path, used = PathPlanner.step(
                self.position, self.path, budget)
            if used == 0:
                self._replan()
                new_pos, self.path, used = PathPlanner.step(
                    self.position, self.path, budget)
                if used == 0:
                    logger.error("Rider %s stuck at %s", self.rider_id,
                                 self.position)
                    break
            self.x, self.y = new_pos
            budget -= used
            self.total_distance += used
            if self.current_order is not None:
                self.current_order.travel_distance = \
                    getattr(self.current_order, "travel_distance", 0) + used
        return self.state

    def remaining_route(self):
        """Points of the rider's remaining route (including current pos)."""
        stops = []
        if self.current_order is not None:
            if self.state == STATE_PICKING_UP:
                stops.append(self.current_order.res_pos)
            stops.append(self.current_order.cus_pos)
        for o in self.orders:
            if o is self.current_order or _status_of(o) == STATUS_COMPLETED:
                continue
            stops.append(o.res_pos)
            stops.append(o.cus_pos)
        return PathPlanner.route(self.position, stops)

    # ----------------------------------------------------------- persistence
    def to_dict(self):
        """Serialise the rider (orders stored as IDs)."""
        return {
            "rider_id": self.rider_id,
            "x": self.x,
            "y": self.y,
            "speed": self.speed,
            "state": self.state,
            "special_case": self.special_case,
            "orders": [getattr(o, "id", None) for o in self.orders],
            "current_order": getattr(self.current_order, "id", None),
            "log": list(self.log),
            "ticks": self.ticks,
            "total_distance": self.total_distance,
        }

    @classmethod
    def from_dict(cls, data, orders_by_id):
        """Rebuild a rider from :meth:`to_dict` output."""
        rider = cls(data["rider_id"], data["x"], data["y"], data["speed"])
        rider.state = data.get("state", STATE_IDLE)
        rider.special_case = data.get("special_case", False)
        rider.orders = [orders_by_id[i] for i in data.get("orders", [])
                        if i in orders_by_id]
        cur = data.get("current_order")
        rider.current_order = orders_by_id.get(cur) if cur is not None \
            else None
        rider.log = list(data.get("log", []))
        rider.ticks = data.get("ticks", 0)
        rider.total_distance = data.get("total_distance", 0)
        if rider.current_order is not None:
            rider._replan()
        return rider

    def __repr__(self):
        return "Rider(id=%s, pos=(%s, %s), state=%s, orders=%d)" % (
            self.rider_id, self.x, self.y, self.state_name, len(self.orders))
