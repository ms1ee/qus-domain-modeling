"""Rider model: movement, state machine and event log."""

import logging

import config
import globalvar
from path_planner import PathPlanner

logger = logging.getLogger(__name__)

STATE_IDLE = 0
STATE_PICKING_UP = 1
STATE_DELIVERING = 2
STATE_NAMES = {STATE_IDLE: "idle", STATE_PICKING_UP: "picking up",
               STATE_DELIVERING: "delivering"}


class Rider:
    """A delivery rider.

    Orders are assigned by appending them to :attr:`orders`.  Each call to
    :meth:`move` advances the rider by one tick.
    """

    def __init__(self, rider_id, x=None, y=None, speed=None):
        self.rider_id = int(rider_id)
        self.x = int(config.RIDER_START_X if x is None else x)
        self.y = int(config.RIDER_START_Y if y is None else y)
        self.speed = int(config.RIDER_SPEED if speed is None else speed)
        if self.speed <= 0:
            self.speed = 1
        self.state = STATE_IDLE
        self.orders = []
        self.special_case = False
        self.path = []
        self.log = []
        self.total_distance = 0
        self.completed_count = 0
        self.planner = PathPlanner()
        self._record("spawn", None)

    # ------------------------------------------------------------------ utils
    @property
    def state_name(self):
        """Human readable state."""
        return STATE_NAMES.get(self.state, "unknown")

    def _record(self, event, order_id):
        """Append an entry to the rider's event log."""
        self.log.append({
            "event": event, "order_id": order_id,
            "time": globalvar.get_value("tick", 0) or 0,
            "x": self.x, "y": self.y, "state": self.state,
        })

    def active_orders(self):
        """Orders that are not completed yet."""
        return [o for o in self.orders if o.status != "completed"]

    def current_order(self):
        """The order currently being worked on (FIFO)."""
        active = self.active_orders()
        return active[0] if active else None

    def expected_free_position(self, exclude=None):
        """Position where the rider will be once current work is done."""
        active = [o for o in self.active_orders() if o is not exclude]
        if active:
            return tuple(active[-1].cus_pos)
        return (self.x, self.y)

    # --------------------------------------------------------------- movement
    def _advance(self, budget):
        """Move along the path using up to ``budget`` units.

        :return: True if the path has been fully travelled.
        """
        while budget > 0 and self.path:
            wx, wy = self.path[0]
            dx, dy = wx - self.x, wy - self.y
            if dx != 0:
                step = min(abs(dx), budget)
                self.x += step if dx > 0 else -step
                budget -= step
                self.total_distance += step
            elif dy != 0:
                step = min(abs(dy), budget)
                self.y += step if dy > 0 else -step
                budget -= step
                self.total_distance += step
            if (self.x, self.y) == (wx, wy):
                self.path.pop(0)
        return not self.path

    def _set_path(self, target):
        """Plan a path from the current position to ``target``."""
        self.path, self.special_case = self.planner.plan((self.x, self.y),
                                                          target)

    def _accept(self, order):
        """Idle -> picking up."""
        self.state = STATE_PICKING_UP
        if order.rider_id is None:
            order.rider_id = self.rider_id
        order.status = "picking_up"
        order.accept_time = globalvar.get_value("tick", 0) or 0
        self._set_path(order.res_pos)
        self._record("accepted_order", order.id)

    def _arrive_merchant(self, order):
        """Picking up -> delivering."""
        self.state = STATE_DELIVERING
        order.status = "delivering"
        order.pickup_time = globalvar.get_value("tick", 0) or 0
        self._record("arrived_at_merchant", order.id)
        self._set_path(order.cus_pos)

    def _deliver(self, order):
        """Delivering -> idle; completes the order and credits funds."""
        order.complete()
        if order in self.orders:
            self.orders.remove(order)
        self.completed_count += 1
        self.state = STATE_IDLE
        self.path = []
        self.special_case = False
        self._record("delivered_to_customer", order.id)
        funds = globalvar.get_value("funds")
        if funds is not None:
            globalvar.set_value("funds", funds + getattr(order, "fee", 0))

    def move(self):
        """Advance one tick: accept, travel and perform state transitions."""
        order = self.current_order()
        if self.state == STATE_IDLE:
            if order is None:
                return
            self._accept(order)
        elif order is None:
            # Consistency recovery: busy without an order.
            logger.warning("Rider %d busy without order; resetting",
                           self.rider_id)
            self.state = STATE_IDLE
            self.path = []
            self.special_case = False
            return
        elif self.state == STATE_PICKING_UP and order.status == "delivering":
            self.state = STATE_DELIVERING
        arrived = self._advance(self.speed)
        if not arrived:
            return
        if self.state == STATE_PICKING_UP:
            self._arrive_merchant(order)
        elif self.state == STATE_DELIVERING:
            self._deliver(order)

    # ------------------------------------------------------------ persistence
    def to_dict(self):
        """Serialise to a JSON compatible dict."""
        return {
            "rider_id": self.rider_id, "x": self.x, "y": self.y,
            "speed": self.speed, "state": self.state,
            "orders": [o.id for o in self.orders],
            "special_case": self.special_case,
            "path": [list(p) for p in self.path], "log": self.log,
            "total_distance": self.total_distance,
            "completed_count": self.completed_count,
        }

    @classmethod
    def from_dict(cls, data, orders_by_id):
        """Rebuild a rider from :meth:`to_dict` output."""
        r = cls(data["rider_id"], data.get("x"), data.get("y"),
                data.get("speed"))
        r.state = int(data.get("state", 0))
        r.orders = [orders_by_id[i] for i in data.get("orders", [])
                    if i in orders_by_id]
        r.special_case = bool(data.get("special_case", False))
        r.path = [tuple(p) for p in data.get("path", [])]
        r.log = list(data.get("log", r.log))
        r.total_distance = data.get("total_distance", 0)
        r.completed_count = data.get("completed_count", 0)
        return r

    def __repr__(self):
        return "Rider(id=%d, pos=(%d,%d), state=%s, orders=%s)" % (
            self.rider_id, self.x, self.y, self.state_name,
            [o.id for o in self.orders])
