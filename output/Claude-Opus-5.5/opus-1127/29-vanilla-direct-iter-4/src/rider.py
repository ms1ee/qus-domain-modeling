"""Rider model: movement, state machine and event log."""

import logging

import config
import globalvar
from path_planner import PathPlanner

logger = logging.getLogger(__name__)

IDLE = 0
PICKING_UP = 1
DELIVERING = 2

STATE_NAMES = {IDLE: "idle", PICKING_UP: "picking up", DELIVERING: "delivering"}


class Rider:
    """A delivery rider.

    Orders are assigned by appending them to ``rider.orders``.  Each call
    to :meth:`move` advances the rider by one tick and performs the state
    transitions idle -> picking up -> delivering -> idle, recording each
    transition in ``rider.log``.
    """

    def __init__(self, rider_id, x=None, y=None, speed=None):
        self.rider_id = rider_id
        self.x = int(config.get("rider_start_x") if x is None else x)
        self.y = int(config.get("rider_start_y") if y is None else y)
        self.speed = int(config.get("rider_speed") if speed is None else speed)
        self.state = IDLE
        self.orders = []
        self.special_case = False
        self.log = []
        self.distance_traveled = 0
        self.delivered_count = 0
        self._ticks = 0
        self._log_event("spawn", None)

    # ------------------------------------------------------------------ util
    def _now(self):
        t = globalvar.get_value("time")
        return t if isinstance(t, int) else self._ticks

    def _log_event(self, event, order_id):
        entry = {
            "event": event,
            "order_id": order_id,
            "time": self._now(),
            "x": self.x,
            "y": self.y,
            "state": self.state,
        }
        self.log.append(entry)
        logger.debug("Rider %s: %s", self.rider_id, entry)

    @property
    def position(self):
        """Current (x, y) position."""
        return (self.x, self.y)

    @property
    def state_name(self):
        """Human readable state name."""
        return STATE_NAMES.get(self.state, "unknown")

    @property
    def current_order(self):
        """The order currently being handled (or None)."""
        if self.state != IDLE and self.orders:
            return self.orders[0]
        return None

    def open_orders(self):
        """Orders on the rider that are not yet completed."""
        return [o for o in self.orders if getattr(o, "status", None) != "completed"]

    def is_idle(self):
        """True when the rider is idle and has no queued orders."""
        return self.state == IDLE and not self.open_orders()

    def remaining_stops(self):
        """Ordered list of remaining target positions for all orders."""
        stops = []
        for i, order in enumerate(self.open_orders()):
            if i == 0 and self.state == DELIVERING:
                stops.append(tuple(order.cus_pos))
            else:
                stops.append(tuple(order.res_pos))
                stops.append(tuple(order.cus_pos))
        return stops

    def planned_route(self):
        """Waypoints of the continuous route through all remaining stops."""
        return PathPlanner.plan_multi_route(self.position, self.remaining_stops())

    # -------------------------------------------------------------- movement
    def _step_towards(self, target):
        tx, ty = int(target[0]), int(target[1])
        self.special_case = PathPlanner.is_special_case(self.x, self.y, tx, ty)
        nx, ny = PathPlanner.next_step(self.x, self.y, tx, ty, self.speed)
        moved = abs(nx - self.x) + abs(ny - self.y)
        self.distance_traveled += moved
        order = self.current_order
        if order is not None and hasattr(order, "travel_distance"):
            order.travel_distance += moved
        self.x, self.y = nx, ny
        return (self.x, self.y) == (tx, ty)

    def _accept(self, order):
        self.state = PICKING_UP
        order.status = "picking_up"
        if getattr(order, "rider_id", None) is None:
            order.rider_id = self.rider_id
        if hasattr(order, "accepted_time"):
            order.accepted_time = self._now()
        self._log_event("accepted_order", order.id)

    def _deliver(self, order):
        order.status = "completed"
        order.completed_time = self._now()
        if order in self.orders:
            self.orders.remove(order)
        self.delivered_count += 1
        self.state = IDLE
        self.special_case = False
        self._log_event("delivered_to_customer", order.id)

    def move(self):
        """Advance the rider by one tick.

        * idle with queued orders -> accept the first order (picking up)
        * picking up -> move toward restaurant; on arrival -> delivering
        * delivering -> move toward customer; on arrival -> idle, order
          completed and removed from ``orders``.
        """
        self._ticks += 1
        # drop any orders already completed elsewhere (in place)
        self.orders[:] = [o for o in self.orders
                          if getattr(o, "status", None) != "completed"]

        if self.state not in (IDLE, PICKING_UP, DELIVERING):
            self.state = IDLE
        if self.state != IDLE and not self.orders:
            # inconsistent state: recover to idle
            self.state = IDLE
            self.special_case = False
            return
        if self.state == IDLE:
            if not self.orders:
                self.special_case = False
                return
            self._accept(self.orders[0])

        order = self.orders[0]
        if self.state == PICKING_UP:
            if self._step_towards(order.res_pos):
                self.state = DELIVERING
                order.status = "delivering"
                if hasattr(order, "pickup_time"):
                    order.pickup_time = self._now()
                self._log_event("arrived_at_merchant", order.id)
        elif self.state == DELIVERING:
            if self._step_towards(order.cus_pos):
                self._deliver(order)

    # ----------------------------------------------------------- persistence
    def to_dict(self):
        """Serialise the rider to a JSON friendly dictionary."""
        return {
            "rider_id": self.rider_id,
            "x": self.x,
            "y": self.y,
            "speed": self.speed,
            "state": self.state,
            "orders": [o.id for o in self.orders],
            "special_case": self.special_case,
            "log": list(self.log),
            "distance_traveled": self.distance_traveled,
            "delivered_count": self.delivered_count,
        }

    @classmethod
    def from_dict(cls, data, orders_by_id=None):
        """Rebuild a rider from :meth:`to_dict` output."""
        rider = cls(data["rider_id"], data.get("x"), data.get("y"),
                    data.get("speed"))
        rider.state = int(data.get("state", IDLE))
        rider.special_case = bool(data.get("special_case", False))
        rider.log = list(data.get("log", rider.log))
        rider.distance_traveled = data.get("distance_traveled", 0)
        rider.delivered_count = data.get("delivered_count", 0)
        orders_by_id = orders_by_id or {}
        rider.orders = [orders_by_id[i] for i in data.get("orders", [])
                        if i in orders_by_id]
        return rider

    def __repr__(self):
        return ("Rider(id=%s, pos=(%d, %d), state=%s, orders=%d)"
                % (self.rider_id, self.x, self.y, self.state_name,
                   len(self.orders)))
