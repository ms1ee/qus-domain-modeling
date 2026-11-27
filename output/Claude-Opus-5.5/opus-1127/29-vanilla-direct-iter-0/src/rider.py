"""Rider model: movement, state machine and event log."""

import logging

import globalvar
from path_planner import PathPlanner

IDLE = 0
PICKING_UP = 1
DELIVERING = 2
STATE_NAMES = {IDLE: "idle", PICKING_UP: "picking up", DELIVERING: "delivering"}

logger = logging.getLogger(__name__)


def _order_positions(order):
    """Return (restaurant, customer) positions for an order-like object."""
    if hasattr(order, "res_pos"):
        return tuple(order.res_pos), tuple(order.cus_pos)
    return (order[0], order[1]), (order[2], order[3])


def _order_id(order):
    return getattr(order, "id", None)


def _set(order, attr, value):
    try:
        setattr(order, attr, value)
    except (AttributeError, TypeError):
        pass


class Rider:
    """A delivery rider.

    Attributes:
        rider_id, x, y, speed, state (0 idle, 1 picking up, 2 delivering),
        orders (list of assigned orders), special_case (bool),
        log (list of event dicts with at least "event" and "order_id").
    """

    def __init__(self, rider_id, x=435, y=385, speed=10):
        self.rider_id = rider_id
        self.x = x
        self.y = y
        self.speed = speed
        self.state = IDLE
        self.orders = []
        self.special_case = False
        self.log = []
        self._log_event("spawn", None)

    # ------------------------------------------------------------------
    def _log_event(self, event, order_id):
        self.log.append({
            "event": event,
            "order_id": order_id,
            "time": globalvar.get_value("time", 0) or 0,
            "x": self.x,
            "y": self.y,
            "state": self.state,
        })
        logger.debug("rider %s %s order %s at (%s,%s)",
                     self.rider_id, event, order_id, self.x, self.y)

    @property
    def state_name(self):
        """Readable state name."""
        return STATE_NAMES.get(self.state, "unknown")

    @property
    def position(self):
        """Current (x, y) position."""
        return (self.x, self.y)

    def is_idle(self):
        """True when the rider has no work."""
        return self.state == IDLE and not self.orders

    def current_target(self):
        """The point the rider is currently heading to, or None."""
        if not self.orders or self.state == IDLE:
            return None
        res, cus = _order_positions(self.orders[0])
        return res if self.state == PICKING_UP else cus

    # ------------------------------------------------------------------
    def _accept(self, order):
        self.state = PICKING_UP
        _set(order, "status", "picking_up")
        if getattr(order, "rider_id", None) is None:
            _set(order, "rider_id", self.rider_id)
        self._log_event("accepted_order", _order_id(order))

    def _deliver(self, order):
        if order in self.orders:
            self.orders.remove(order)
        _set(order, "status", "completed")
        _set(order, "complete_time", globalvar.get_value("time", 0) or 0)
        self.state = IDLE
        self.special_case = False
        self._log_event("delivered_to_customer", _order_id(order))

    def _handle_arrival(self, order):
        res, cus = _order_positions(order)
        if self.state == PICKING_UP and self.position == tuple(res):
            self.state = DELIVERING
            _set(order, "status", "delivering")
            _set(order, "pickup_time", globalvar.get_value("time", 0) or 0)
            self._log_event("arrived_at_merchant", _order_id(order))
        if self.state == DELIVERING and self.position == tuple(cus):
            self._deliver(order)

    def move(self):
        """Advance the rider by one tick, performing state transitions."""
        if self.state == IDLE:
            if not self.orders:
                self.special_case = False
                return
            self._accept(self.orders[0])
        if not self.orders:
            self.state = IDLE
            return
        order = self.orders[0]
        target = self.current_target()
        if self.position != tuple(target):
            self.x, self.y, self.special_case = PathPlanner.step(
                self.x, self.y, target, self.speed)
        if self.position == tuple(target):
            self._handle_arrival(order)

    # ------------------------------------------------------------------
    def to_dict(self):
        """Serialize the rider (orders are stored by id)."""
        return {
            "rider_id": self.rider_id,
            "x": self.x,
            "y": self.y,
            "speed": self.speed,
            "state": self.state,
            "orders": [_order_id(o) for o in self.orders],
            "special_case": self.special_case,
            "log": self.log,
        }

    def __repr__(self):
        return "Rider(id=%s, pos=(%s,%s), state=%s, orders=%d)" % (
            self.rider_id, self.x, self.y, self.state, len(self.orders))
