"""Rider model: movement, state machine and status log."""

import logging

import globalvar
from path_planner import PathPlanner, to_grid_center

logger = logging.getLogger(__name__)


class RiderState:
    """Rider state enumeration."""
    IDLE = 0
    PICKING_UP = 1
    DELIVERING = 2
    NAMES = {0: "idle", 1: "picking up", 2: "delivering"}


DEFAULT_X = 435
DEFAULT_Y = 385
DEFAULT_SPEED = 10


def _order_positions(order):
    """Return (restaurant_pos, customer_pos) for an Order or a 4-list."""
    if hasattr(order, "res_pos") and hasattr(order, "cus_pos"):
        return tuple(order.res_pos), tuple(order.cus_pos)
    rx, ry, cx, cy = order
    return ((to_grid_center(rx), to_grid_center(ry)),
            (to_grid_center(cx), to_grid_center(cy)))


def _order_id(order):
    return getattr(order, "id", None)


class Rider:
    """A delivery rider.

    Attributes:
        rider_id, x, y, speed, state (0/1/2), orders (list), special_case,
        log (list of dicts with keys time, event, order_id, x, y, state).
    """

    def __init__(self, rider_id, x=None, y=None, speed=None):
        cfg = globalvar.get_value("config")
        self.rider_id = rider_id
        self.x = int(x if x is not None else getattr(cfg, "initial_rider_x", DEFAULT_X))
        self.y = int(y if y is not None else getattr(cfg, "initial_rider_y", DEFAULT_Y))
        self.speed = int(speed if speed is not None
                         else getattr(cfg, "default_speed", DEFAULT_SPEED))
        self.state = RiderState.IDLE
        self.orders = []
        self.special_case = False
        self.log = []
        self.route_points = []
        self._route_target = None
        self._record("spawn", None)

    # ------------------------------------------------------------------ helpers
    @property
    def position(self):
        """Current (x, y) tuple."""
        return (self.x, self.y)

    @property
    def state_name(self):
        """Human readable state."""
        return RiderState.NAMES.get(self.state, str(self.state))

    def is_idle(self):
        """True when idle with no queued orders."""
        return self.state == RiderState.IDLE and not self.orders

    def _record(self, event, order):
        entry = {
            "time": globalvar.get_value("tick", 0),
            "event": event,
            "order_id": _order_id(order) if order is not None else None,
            "x": self.x,
            "y": self.y,
            "state": self.state,
        }
        self.log.append(entry)
        logger.debug("Rider %s: %s", self.rider_id, entry)

    def _reset_route(self):
        self.route_points = []
        self._route_target = None
        self.special_case = False

    def _advance(self, target):
        """Move up to ``speed`` units along the planned path to target."""
        if self._route_target != target or not self.route_points:
            self.route_points = PathPlanner.plan_route(self.position, target)
            self.special_case = PathPlanner.is_special_case(self.position, target)
            self._route_target = target
        remaining = self.speed
        while remaining > 0 and self.route_points:
            wx, wy = self.route_points[0]
            dx = wx - self.x
            dy = wy - self.y
            if dx:
                step = min(remaining, abs(dx))
                self.x += step if dx > 0 else -step
                remaining -= step
            elif dy:
                step = min(remaining, abs(dy))
                self.y += step if dy > 0 else -step
                remaining -= step
            if (self.x, self.y) == (wx, wy):
                self.route_points.pop(0)

    # --------------------------------------------------------------------- tick
    def move(self):
        """Advance the rider by one tick.

        Handles the state machine:
          idle -> picking up (order accepted),
          picking up -> delivering (arrived at merchant),
          delivering -> idle (delivered to customer).
        """
        if self.state == RiderState.IDLE:
            if not self.orders:
                return
            order = self.orders[0]
            self.state = RiderState.PICKING_UP
            if hasattr(order, "status"):
                order.status = "picking_up"
            self._reset_route()
            self._record("accepted_order", order)

        if not self.orders:
            self.state = RiderState.IDLE
            self._reset_route()
            return

        order = self.orders[0]
        res_pos, cus_pos = _order_positions(order)
        target = res_pos if self.state == RiderState.PICKING_UP else cus_pos

        if self.position != target:
            self._advance(target)

        if self.position == target:
            if self.state == RiderState.PICKING_UP:
                self.state = RiderState.DELIVERING
                if hasattr(order, "mark_picked_up"):
                    order.mark_picked_up()
                self._reset_route()
                self._record("arrived_at_merchant", order)
            else:
                self.orders.pop(0)
                if hasattr(order, "mark_completed"):
                    order.mark_completed()
                elif hasattr(order, "status"):
                    order.status = "completed"
                self.state = RiderState.IDLE
                self._reset_route()
                self._record("delivered_to_customer", order)

    # ------------------------------------------------------------ persistence
    def to_dict(self):
        """Serialise the rider."""
        return {
            "rider_id": self.rider_id, "x": self.x, "y": self.y,
            "speed": self.speed, "state": self.state,
            "special_case": self.special_case,
            "orders": [_order_id(o) for o in self.orders],
            "log": list(self.log),
        }

    def __repr__(self):
        return "Rider(id=%s, pos=(%d,%d), state=%s, orders=%d)" % (
            self.rider_id, self.x, self.y, self.state, len(self.orders))
