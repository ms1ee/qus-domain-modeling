"""Rider model: movement, state transitions and status log."""

import logging

import globalvar
from order_model import OrderStatus
from path_planner import DEFAULT_SPEED, PathPlanner, manhattan

logger = logging.getLogger(__name__)

DEFAULT_SPAWN = (400, 400)


class RiderState:
    """Rider state enumeration."""
    IDLE = 0
    PICKING_UP = 1
    DELIVERING = 2
    NAMES = {0: "idle", 1: "picking up", 2: "delivering"}

    @classmethod
    def name(cls, state):
        return cls.NAMES.get(state, "unknown")


class Rider:
    """A delivery rider.

    Orders are assigned by appending them to ``rider.orders``. Each call to
    :meth:`move` advances the rider by one tick, performing state transitions
    and recording them in ``rider.log``.
    """

    _planner = PathPlanner()

    def __init__(self, rider_id, x=None, y=None, speed=None):
        spawn = globalvar.get_value("spawn_position") or DEFAULT_SPAWN
        self.rider_id = rider_id
        self.x = int(spawn[0] if x is None else x)
        self.y = int(spawn[1] if y is None else y)
        if speed is None:
            speed = globalvar.get_value("default_speed") or DEFAULT_SPEED
        self.speed = int(speed)
        self.state = RiderState.IDLE
        self.orders = []
        self.special_case = False
        self.log = []
        self.path = []
        self.route = None
        self.current_order = None
        self.total_distance = 0
        self.completed_count = 0
        self._ticks = 0
        self._record("spawn", None)

    # Helpers -----------------------------------------------------------
    @property
    def position(self):
        return (self.x, self.y)

    def _now(self):
        t = globalvar.get_value("time")
        return t if isinstance(t, int) else self._ticks

    def _record(self, event, order_id):
        self.log.append({
            "time": self._now(),
            "event": event,
            "order_id": order_id,
            "x": self.x,
            "y": self.y,
            "state": self.state,
            "state_name": RiderState.name(self.state),
        })

    def _plan_to(self, target):
        route = self._planner.plan(self.position, target, self.speed)
        self.route = route
        self.path = route.waypoints()[1:]
        self.special_case = route.special_case

    def pending_orders(self):
        """Orders assigned to this rider and not yet completed."""
        return [o for o in self.orders if o.status != OrderStatus.COMPLETED]

    def has_pending_orders(self):
        return bool(self.pending_orders())

    def remaining_work(self):
        """Return (remaining_distance, end_position) for all assigned work."""
        total = 0
        pos = self.position
        cur = self.current_order
        if cur is not None and cur.status != OrderStatus.COMPLETED:
            if self.state == RiderState.PICKING_UP:
                total += manhattan(pos, cur.res_pos) + manhattan(cur.res_pos,
                                                                 cur.cus_pos)
                pos = cur.cus_pos
            elif self.state == RiderState.DELIVERING:
                total += manhattan(pos, cur.cus_pos)
                pos = cur.cus_pos
        for o in self.pending_orders():
            if o is cur:
                continue
            total += manhattan(pos, o.res_pos) + manhattan(o.res_pos, o.cus_pos)
            pos = o.cus_pos
        return total, pos

    def reset_to_idle(self):
        """Release current work and return to the idle state."""
        self.state = RiderState.IDLE
        self.current_order = None
        self.path = []
        self.route = None
        self.special_case = False

    # Movement ----------------------------------------------------------
    def _accept_next_order(self):
        order = None
        for o in list(self.orders):
            if o.status == OrderStatus.COMPLETED:
                self.orders.remove(o)
                continue
            order = o
            break
        if order is None:
            return False
        self.current_order = order
        if order.rider_id != self.rider_id:
            order.assign_to(self.rider_id)
        order.mark_picking_up(self._now())
        self.state = RiderState.PICKING_UP
        self._plan_to(order.res_pos)
        self._record("accepted_order", order.id)
        return True

    def _advance(self, budget):
        moved = 0
        while budget > 0 and self.path:
            tx, ty = self.path[0]
            if (self.x, self.y) == (tx, ty):
                self.path.pop(0)
                continue
            if self.x != tx:
                step = min(budget, abs(tx - self.x))
                self.x += step if tx > self.x else -step
            else:
                step = min(budget, abs(ty - self.y))
                self.y += step if ty > self.y else -step
            budget -= step
            moved += step
            if (self.x, self.y) == (tx, ty):
                self.path.pop(0)
        self.total_distance += moved
        if self.current_order is not None:
            self.current_order.travel_distance += moved

    def _deliver(self, order):
        order.complete(self._now())
        if order in self.orders:
            self.orders.remove(order)
        self.completed_count += 1
        self.reset_to_idle()
        self._record("delivered_to_customer", order.id)
        funds = globalvar.get_value("funds")
        bonus = globalvar.get_value("delivery_bonus") or 0
        if isinstance(funds, int) and bonus:
            globalvar.set_value("funds", funds + bonus)

    def _process_arrivals(self):
        for _ in range(3):
            order = self.current_order
            if order is None:
                return
            if self.state == RiderState.PICKING_UP:
                if self.position == order.res_pos:
                    order.mark_picked_up(self._now())
                    self.state = RiderState.DELIVERING
                    self._plan_to(order.cus_pos)
                    self._record("arrived_at_merchant", order.id)
                    continue
                if not self.path:
                    self._plan_to(order.res_pos)
                return
            if self.state == RiderState.DELIVERING:
                if self.position == order.cus_pos:
                    self._deliver(order)
                    return
                if not self.path:
                    self._plan_to(order.cus_pos)
                return
            return

    def move(self):
        """Advance one tick: accept orders, move, and handle arrivals."""
        self._ticks += 1
        if self.state == RiderState.IDLE:
            if not self._accept_next_order():
                return
        order = self.current_order
        if order is None or order.status == OrderStatus.COMPLETED:
            self.reset_to_idle()
            return
        self._process_arrivals()
        if self.state == RiderState.IDLE:
            return
        self._advance(self.speed)
        self._process_arrivals()

    # Persistence -------------------------------------------------------
    def to_dict(self):
        return {
            "rider_id": self.rider_id,
            "x": self.x,
            "y": self.y,
            "speed": self.speed,
            "state": self.state,
            "special_case": self.special_case,
            "order_ids": [o.id for o in self.orders],
            "current_order_id": (self.current_order.id
                                 if self.current_order else None),
            "log": self.log,
            "total_distance": self.total_distance,
            "completed_count": self.completed_count,
        }

    @classmethod
    def from_dict(cls, data, orders_by_id):
        rider = cls(data["rider_id"], data["x"], data["y"], data["speed"])
        rider.state = data.get("state", RiderState.IDLE)
        rider.special_case = data.get("special_case", False)
        rider.orders = [orders_by_id[i] for i in data.get("order_ids", [])
                        if i in orders_by_id]
        cur = data.get("current_order_id")
        rider.current_order = orders_by_id.get(cur) if cur is not None else None
        rider.log = list(data.get("log", []))
        rider.total_distance = data.get("total_distance", 0)
        rider.completed_count = data.get("completed_count", 0)
        if rider.current_order is None:
            rider.state = RiderState.IDLE
        return rider

    def __repr__(self):
        return "Rider(#%d at (%d,%d) %s)" % (self.rider_id, self.x, self.y,
                                            RiderState.name(self.state))
