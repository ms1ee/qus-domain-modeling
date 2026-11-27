"""Rider model: movement, state machine and status log."""

import logging

import globalvar
from path_planner import PathPlanner, clamp
from order_model import (ORDER_COMPLETED, ORDER_PICKING_UP, ORDER_DELIVERING)

logger = logging.getLogger(__name__)


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
    """A delivery rider moving on the grid."""

    def __init__(self, rider_id, x=None, y=None, speed=None):
        self.rider_id = rider_id
        self.x = int(x if x is not None else globalvar.get_value("spawn_x", 400))
        self.y = int(y if y is not None else globalvar.get_value("spawn_y", 400))
        self.speed = int(speed if speed is not None
                         else globalvar.get_value("rider_speed", 100))
        self.state = RiderState.IDLE
        self.orders = []
        self.special_case = False
        self.log = []
        self.path = []
        self.current_order = None
        self.completed_orders = []
        self.distance_travelled = 0
        self._planner = PathPlanner()
        self._log_event("spawn", None)

    # ------------------------------------------------------------------ helpers
    def _log_event(self, event, order_id):
        entry = {
            "time": globalvar.get_value("tick", 0) or 0,
            "x": self.x,
            "y": self.y,
            "event": event,
            "order_id": order_id,
            "state": self.state,
        }
        self.log.append(entry)
        logger.info("Rider %s: %s (order %s) at %s", self.rider_id, event,
                    order_id, (self.x, self.y))

    def pending_orders(self):
        """Orders assigned to this rider that are not completed."""
        return [o for o in self.orders if o.status != ORDER_COMPLETED]

    def has_pending_orders(self):
        return bool(self.pending_orders())

    def final_position(self):
        """Position where the rider will be after finishing all orders."""
        pending = self.pending_orders()
        if pending:
            return pending[-1].cus_pos
        return (self.x, self.y)

    def _plan_to(self, target):
        route = self._planner.plan((self.x, self.y), target, self.speed)
        self.path = list(route.waypoints[1:])
        self.special_case = route.special_case

    def _advance(self, target):
        """Move up to ``speed`` units along the planned path."""
        if (self.x, self.y) != tuple(target) and (
                not self.path or self.path[-1] != tuple(target)):
            self._plan_to(target)
        remaining = max(0, self.speed)
        moved = 0
        while remaining > 0 and self.path:
            tx, ty = self.path[0]
            dx, dy = tx - self.x, ty - self.y
            if dx != 0 and dy != 0:
                # Should not happen (segments are axis-aligned); fix by
                # inserting a corner point.
                self.path.insert(0, (tx, self.y))
                continue
            dist = abs(dx) + abs(dy)
            if dist <= remaining:
                self.x, self.y = tx, ty
                remaining -= dist
                moved += dist
                self.path.pop(0)
            else:
                if dx:
                    self.x += remaining if dx > 0 else -remaining
                else:
                    self.y += remaining if dy > 0 else -remaining
                moved += remaining
                remaining = 0
        self.x = clamp(self.x)
        self.y = clamp(self.y)
        self.distance_travelled += moved
        if self.current_order is not None:
            self.current_order.travel_distance += moved

    def _reset_idle(self):
        self.state = RiderState.IDLE
        self.current_order = None
        self.path = []
        self.special_case = False

    # ------------------------------------------------------------------- tick
    def move(self):
        """Advance the rider by one tick.

        * Idle with a pending order -> accept it (state 1).
        * Picking up -> move toward restaurant; on arrival -> state 2.
        * Delivering -> move toward customer; on arrival -> complete, state 0.
        """
        tick = globalvar.get_value("tick", 0) or 0
        if self.state == RiderState.IDLE:
            pending = self.pending_orders()
            if not pending:
                self.special_case = False
                return
            order = pending[0]
            self.current_order = order
            if order.rider_id != self.rider_id:
                order.assign_to(self.rider_id)
            order.status = ORDER_PICKING_UP
            self.state = RiderState.PICKING_UP
            self._plan_to(order.res_pos)
            self._log_event("accepted_order", order.id)
            return

        order = self.current_order
        if order is None or order not in self.orders or order.is_completed():
            # Inconsistent state: recover to idle.
            logger.warning("Rider %s recovered from inconsistent state",
                           self.rider_id)
            self._reset_idle()
            return

        if self.state == RiderState.PICKING_UP:
            self._advance(order.res_pos)
            if (self.x, self.y) == tuple(order.res_pos):
                self.state = RiderState.DELIVERING
                order.status = ORDER_DELIVERING
                order.pickup_time = tick
                self._log_event("arrived_at_merchant", order.id)
                self._plan_to(order.cus_pos)
        elif self.state == RiderState.DELIVERING:
            self._advance(order.cus_pos)
            if (self.x, self.y) == tuple(order.cus_pos):
                order.status = ORDER_COMPLETED
                order.completion_time = tick
                order.time_taken = tick - order.start_time
                self._log_event("delivered_to_customer", order.id)
                self.orders.remove(order)
                self.completed_orders.append(order)
                self._reset_idle()
        else:
            self._reset_idle()

    # ------------------------------------------------------------- reporting
    def to_dict(self):
        return {
            "rider_id": self.rider_id,
            "x": self.x,
            "y": self.y,
            "speed": self.speed,
            "state": self.state,
            "orders": [o.id for o in self.orders],
            "completed_orders": [o.id for o in self.completed_orders],
            "special_case": self.special_case,
            "distance_travelled": self.distance_travelled,
            "log": list(self.log),
        }

    def __repr__(self):
        return "Rider(id={}, pos=({}, {}), state={})".format(
            self.rider_id, self.x, self.y, RiderState.name(self.state))
