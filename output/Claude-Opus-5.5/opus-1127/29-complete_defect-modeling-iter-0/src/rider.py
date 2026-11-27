"""Rider model: state, movement and status log."""

import logging
from enum import IntEnum

import globalvar
from grid_map import CELL_SIZE, MAP_SIZE, clamp_coordinate
from path_planner import PathPlanner

logger = logging.getLogger(__name__)


class RiderState(IntEnum):
    """Rider status enumeration."""
    IDLE = 0
    PICKING_UP = 1
    DELIVERING = 2


IDLE = 0
PICKING_UP = 1
DELIVERING = 2

STATE_NAMES = {IDLE: "idle", PICKING_UP: "picking up", DELIVERING: "delivering"}


def _config_value(key, default):
    cfg = globalvar.get_value("config")
    if cfg is None:
        return default
    try:
        value = cfg.get(key, default)
    except Exception:  # pragma: no cover - defensive
        return default
    return default if value is None else value


class Rider:
    """A delivery rider moving along the streets of the grid."""

    def __init__(self, rider_id, x=None, y=None, speed=None):
        self.rider_id = int(rider_id)
        self.map_size = int(_config_value("map_size", MAP_SIZE))
        self.cell_size = int(_config_value("cell_size", CELL_SIZE))
        if x is None:
            x = _config_value("rider_start_x", 400)
        if y is None:
            y = _config_value("rider_start_y", 400)
        if speed is None:
            speed = _config_value("rider_speed", 50)
        self.x = clamp_coordinate(x, self.map_size)
        self.y = clamp_coordinate(y, self.map_size)
        self.speed = max(1, int(speed))
        self.state = IDLE
        self.orders = []
        self.special_case = False
        self.log = []
        self.path = []
        self.current_order = None
        self.target = None
        self.distance_travelled = 0
        self.delivered_count = 0
        self._planner = PathPlanner(self.cell_size, self.map_size)
        self._record("spawn", None)

    # helpers ---------------------------------------------------------------
    @property
    def state_name(self):
        return STATE_NAMES.get(self.state, "unknown")

    @property
    def position(self):
        return (self.x, self.y)

    @staticmethod
    def _now():
        return globalvar.get_value("tick", 0) or 0

    def _record(self, event, order_id):
        entry = {"time": self._now(), "event": event, "order_id": order_id,
                 "x": self.x, "y": self.y, "state": int(self.state),
                 "state_name": self.state_name}
        self.log.append(entry)
        limit = int(_config_value("max_log_entries", 5000))
        if limit > 0 and len(self.log) > limit:
            del self.log[:len(self.log) - limit]

    def active_orders(self):
        """Orders assigned to this rider that are not completed yet."""
        return [o for o in self.orders if getattr(o, "status", "") != "completed"]

    def _next_order(self):
        for order in self.orders:
            if getattr(order, "status", "") != "completed":
                return order
        return None

    def _plan_to(self, target):
        self.target = (int(target[0]), int(target[1]))
        self.special_case = self._planner.is_directly_above_or_below(
            (self.x, self.y), self.target)
        self.path = self._planner.find_path((self.x, self.y), self.target)[1:]

    def remaining_route(self):
        """Waypoints still to be travelled (current leg)."""
        return [(self.x, self.y)] + list(self.path)

    def _advance(self):
        remaining = self.speed
        while remaining > 0 and self.path:
            tx, ty = self.path[0]
            dx, dy = tx - self.x, ty - self.y
            dist = abs(dx) + abs(dy)
            if dist <= remaining:
                self.x, self.y = tx, ty
                self.path.pop(0)
                remaining -= dist
                self.distance_travelled += dist
                continue
            if dx != 0:
                step = min(abs(dx), remaining)
                self.x += step if dx > 0 else -step
            else:
                step = min(abs(dy), remaining)
                self.y += step if dy > 0 else -step
            remaining -= step
            self.distance_travelled += step

    def _reset_to_idle(self):
        self.state = IDLE
        self.current_order = None
        self.target = None
        self.path = []
        self.special_case = False

    # tick ------------------------------------------------------------------
    def move(self):
        """Advance the rider by one tick.

        Handles state transitions (idle -> picking up -> delivering -> idle)
        and records the corresponding log entries.
        """
        tick = self._now()
        if self.state == IDLE:
            order = self._next_order()
            if order is None:
                self.special_case = False
                return
            if order.rider_id is None:
                order.assign_to(self.rider_id)
            order.mark_accepted(tick, self.rider_id)
            self.current_order = order
            self.state = PICKING_UP
            self._plan_to(order.restaurant)
            self._record("accepted_order", order.id)
            return

        order = self.current_order
        if order is None or order not in self.orders or order.status == "completed":
            logger.warning("Rider %d inconsistent state; resetting", self.rider_id)
            self._reset_to_idle()
            return
        order.active_ticks += 1
        if self.target is None:
            self.target = order.restaurant if self.state == PICKING_UP else order.customer
        if not self.path and (self.x, self.y) != self.target:
            self._plan_to(self.target)
        self._advance()
        if self.path or (self.x, self.y) != self.target:
            return
        if self.state == PICKING_UP:
            order.mark_picked_up(tick)
            self.state = DELIVERING
            self._plan_to(order.customer)
            self._record("arrived_at_merchant", order.id)
        elif self.state == DELIVERING:
            order.complete(tick)
            self.orders.remove(order)
            self.delivered_count += 1
            self._reset_to_idle()
            self._record("delivered_to_customer", order.id)

    # persistence -----------------------------------------------------------
    def to_dict(self):
        return {"rider_id": self.rider_id, "x": self.x, "y": self.y,
                "speed": self.speed, "state": int(self.state),
                "orders": [o.id for o in self.orders],
                "current_order": self.current_order.id if self.current_order else None,
                "special_case": self.special_case, "log": list(self.log),
                "distance_travelled": self.distance_travelled,
                "delivered_count": self.delivered_count}

    @classmethod
    def from_dict(cls, data, orders_by_id=None):
        rider = cls(data["rider_id"], data.get("x"), data.get("y"), data.get("speed"))
        rider.log = list(data.get("log", rider.log))
        rider.distance_travelled = data.get("distance_travelled", 0)
        rider.delivered_count = data.get("delivered_count", 0)
        orders_by_id = orders_by_id or {}
        rider.orders = [orders_by_id[i] for i in data.get("orders", [])
                        if i in orders_by_id]
        state = int(data.get("state", IDLE))
        cur_id = data.get("current_order")
        if state != IDLE and cur_id in orders_by_id and \
                orders_by_id[cur_id] in rider.orders:
            rider.state = state
            rider.current_order = orders_by_id[cur_id]
            target = (rider.current_order.restaurant if state == PICKING_UP
                      else rider.current_order.customer)
            rider._plan_to(target)
        return rider

    def __repr__(self):
        return "Rider(#%d (%d,%d) %s)" % (self.rider_id, self.x, self.y,
                                          self.state_name)
