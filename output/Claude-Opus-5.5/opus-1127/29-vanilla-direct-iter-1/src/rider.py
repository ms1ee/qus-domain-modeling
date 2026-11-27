"""Rider model: movement, state and orders."""

import logging

import globalvar
from path_planner import PathPlanner

logger = logging.getLogger(__name__)

IDLE = 0
PICKING_UP = 1
DELIVERING = 2
STATE_NAMES = {IDLE: "idle", PICKING_UP: "picking up", DELIVERING: "delivering"}

START_X = 435
START_Y = 385
DEFAULT_SPEED = 10


def _now():
    t = globalvar.get_value("time")
    return t if isinstance(t, int) else 0


class Rider:
    """A delivery rider.

    Orders are assigned by appending them to ``rider.orders``; each call
    to :meth:`move` advances one tick and performs state transitions.
    """

    def __init__(self, rider_id, x=START_X, y=START_Y, speed=DEFAULT_SPEED):
        self.rider_id = rider_id
        self.x = x
        self.y = y
        self.speed = speed
        self.state = IDLE
        self.orders = []
        self.special_case = False
        self.completed_orders = []
        self.total_distance = 0
        self.log = []
        self._log_event("spawn", None)

    # ------------------------------------------------------------------
    def _log_event(self, event, order_id):
        self.log.append({
            "event": event,
            "order_id": order_id,
            "time": _now(),
            "x": self.x,
            "y": self.y,
            "state": self.state,
        })
        logger.debug("rider %s %s order=%s at (%s,%s)",
                     self.rider_id, event, order_id, self.x, self.y)

    @property
    def state_name(self):
        """Human readable state."""
        return STATE_NAMES.get(self.state, "unknown")

    @property
    def position(self):
        """Current (x, y)."""
        return (self.x, self.y)

    @property
    def current_order(self):
        """Order currently being handled (or None)."""
        return self.orders[0] if self.orders else None

    def _step_toward(self, target):
        self.special_case = PathPlanner.is_vertical_special_case(
            self.position, target)
        nx, ny = PathPlanner.step(self.position, target, self.speed)
        self.total_distance += abs(nx - self.x) + abs(ny - self.y)
        self.x, self.y = nx, ny
        return (self.x, self.y) == tuple(target)

    def _accept(self, order):
        if getattr(order, "rider_id", None) is None:
            try:
                order.assign_to(self.rider_id)
            except AttributeError:
                pass
        order.status = "picking_up"
        self.state = PICKING_UP
        self._log_event("accepted_order", order.id)

    def move(self):
        """Advance one tick of movement and state transitions."""
        if self.state == IDLE:
            if not self.orders:
                self.special_case = False
                return
            self._accept(self.orders[0])

        order = self.current_order
        if order is None:
            self.state = IDLE
            return

        if self.state == PICKING_UP:
            if self._step_toward(order.res_pos):
                self.state = DELIVERING
                order.status = "delivering"
                order.pickup_time = _now()
                self._log_event("arrived_at_merchant", order.id)
        elif self.state == DELIVERING:
            if self._step_toward(order.cus_pos):
                order.status = "completed"
                order.complete_time = _now()
                self.orders.remove(order)
                self.completed_orders.append(order.id)
                self.state = IDLE
                self.special_case = False
                self._log_event("delivered_to_customer", order.id)

    def remaining_path(self):
        """Waypoints the rider still needs to travel for all orders."""
        points = [self.position]
        for idx, order in enumerate(self.orders):
            if idx == 0 and self.state == DELIVERING:
                points.append(order.cus_pos)
            else:
                points.extend([order.res_pos, order.cus_pos])
        return PathPlanner.compute_multi_path(points)

    def to_dict(self):
        """Serialise rider to a JSON friendly dict."""
        return {
            "rider_id": self.rider_id,
            "x": self.x,
            "y": self.y,
            "speed": self.speed,
            "state": self.state,
            "orders": [o.id for o in self.orders],
            "special_case": self.special_case,
            "completed_orders": list(self.completed_orders),
            "total_distance": self.total_distance,
            "log": list(self.log),
        }

    def __repr__(self):
        return "Rider(id=%s, pos=(%s,%s), state=%s, orders=%d)" % (
            self.rider_id, self.x, self.y, self.state, len(self.orders))
