"""Rider model: movement, state machine and event log."""

import logging

import globalvar
from path_planner import PathPlanner

logger = logging.getLogger(__name__)

STATE_IDLE = 0
STATE_PICKING_UP = 1
STATE_DELIVERING = 2
STATE_NAMES = {STATE_IDLE: "idle", STATE_PICKING_UP: "picking up",
               STATE_DELIVERING: "delivering"}

DEFAULT_SPEED = 50
DEFAULT_X = 400
DEFAULT_Y = 400
DEFAULT_ORDER_INCOME = 100


class Rider:
    """A delivery rider.

    Orders are assigned by appending them to ``rider.orders``; ``move()``
    then picks them up in order, performing state transitions and logging.
    """

    def __init__(self, rider_id, x=None, y=None, speed=None):
        cfg = globalvar.get_value("config") or {}
        self.rider_id = rider_id
        self.x = int(x if x is not None else cfg.get("spawn_x", DEFAULT_X))
        self.y = int(y if y is not None else cfg.get("spawn_y", DEFAULT_Y))
        self.speed = int(speed if speed is not None
                         else cfg.get("rider_speed", DEFAULT_SPEED))
        if self.speed <= 0:
            self.speed = DEFAULT_SPEED
        self.state = STATE_IDLE
        self.orders = []
        self.special_case = False
        self.current_order = None
        self.path = []
        self.ticks = 0
        self.total_distance = 0
        self.completed_count = 0
        self.log = []
        self._log("spawn", None)

    # ------------------------------------------------------------------
    def _now(self):
        t = globalvar.get_value("time")
        return t if t is not None else self.ticks

    def _log(self, event, order_id):
        entry = {"event": event, "order_id": order_id, "time": self._now(),
                 "x": self.x, "y": self.y, "state": self.state}
        self.log.append(entry)
        logger.debug("Rider %s: %s", self.rider_id, entry)

    def state_name(self):
        """Human readable state."""
        return STATE_NAMES.get(self.state, "unknown")

    def active_orders(self):
        """Orders not yet completed."""
        return [o for o in self.orders if o.status != "completed"]

    def is_available(self):
        """True when idle with no queued orders."""
        return self.state == STATE_IDLE and not self.active_orders()

    def queue_end_position(self):
        """Position where the rider will be after all queued orders."""
        active = self.active_orders()
        if active:
            return tuple(active[-1].cus_pos)
        return (self.x, self.y)

    # ------------------------------------------------------------------
    def _plan(self, target):
        self.special_case = PathPlanner.is_special_case((self.x, self.y),
                                                        target)
        self.path = PathPlanner.find_path((self.x, self.y), target)

    def _start_next_order(self):
        for order in self.orders:
            if order.status != "completed":
                break
        else:
            return False
        self.current_order = order
        if order.rider_id is None:
            order.assign_to(self.rider_id)
        self.state = STATE_PICKING_UP
        order.status = "picking_up"
        order.accept_time = self._now()
        to_res = PathPlanner.path_length(
            (self.x, self.y),
            PathPlanner.find_path((self.x, self.y), order.res_pos))
        order.distance = to_res + order.trip_distance
        self._plan(order.res_pos)
        self._log("accepted_order", order.id)
        return True

    def _advance(self, budget):
        while budget > 0 and self.path:
            tx, ty = self.path[0]
            if self.x != tx:
                step = min(budget, abs(tx - self.x))
                self.x += step if tx > self.x else -step
            else:
                step = min(budget, abs(ty - self.y))
                self.y += step if ty > self.y else -step
            budget -= step
            self.total_distance += step
            if (self.x, self.y) == (tx, ty):
                self.path.pop(0)
            if step == 0:
                self.path.pop(0)
        return budget

    def _handle_arrival(self):
        order = self.current_order
        if self.state == STATE_PICKING_UP:
            self.state = STATE_DELIVERING
            order.status = "delivering"
            order.pickup_time = self._now()
            self._log("arrived_at_merchant", order.id)
            self._plan(order.cus_pos)
        elif self.state == STATE_DELIVERING:
            order.status = "completed"
            order.complete_time = self._now()
            order.time_taken = order.complete_time - order.create_time
            if order.time_taken and order.time_taken > 0:
                order.efficiency = round((order.distance or 0)
                                         / order.time_taken, 2)
            self.state = STATE_IDLE
            self.special_case = False
            if order in self.orders:
                self.orders.remove(order)
            self.current_order = None
            self.completed_count += 1
            funds = globalvar.get_value("funds")
            if funds is not None:
                cfg = globalvar.get_value("config") or {}
                globalvar.set_value(
                    "funds",
                    funds + cfg.get("order_income", DEFAULT_ORDER_INCOME))
            self._log("delivered_to_customer", order.id)

    def move(self):
        """Advance the rider by one tick."""
        self.ticks += 1
        if self.state == STATE_IDLE or self.current_order is None:
            self.state = STATE_IDLE
            if not self._start_next_order():
                return
        budget = self.speed
        guard = 0
        while self.state != STATE_IDLE and guard < 10:
            guard += 1
            budget = self._advance(budget)
            if self.path:
                break
            self._handle_arrival()

    # ------------------------------------------------------------------
    def to_dict(self):
        """Serialisable representation."""
        return {
            "rider_id": self.rider_id, "x": self.x, "y": self.y,
            "speed": self.speed, "state": self.state,
            "orders": [o.id for o in self.orders],
            "special_case": self.special_case,
            "total_distance": self.total_distance,
            "completed_count": self.completed_count,
            "log": list(self.log),
        }

    def __repr__(self):
        return "Rider(id=%s, pos=(%d,%d), state=%s, orders=%s)" % (
            self.rider_id, self.x, self.y, self.state_name(),
            [o.id for o in self.orders])
