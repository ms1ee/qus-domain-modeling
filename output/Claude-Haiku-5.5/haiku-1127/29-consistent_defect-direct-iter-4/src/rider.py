"""Rider model: state machine, street movement and delivery event logging."""

import logging

import globalvar
from order_model import ASSIGNED, PICKED_UP, COMPLETED  # noqa: F401
from path_planner import PathPlanner

logger = logging.getLogger(__name__)

IDLE = 0
PICKING_UP = 1
DELIVERING = 2

STATE_NAMES = {
    IDLE: "idle",
    PICKING_UP: "picking up",
    DELIVERING: "delivering",
}

SPAWN_X = 400
SPAWN_Y = 400
DEFAULT_SPEED = 20


class Rider:
    """A delivery rider that moves along streets and serves orders.

    Attributes:
        rider_id: Unique identifier.
        x, y: Current position.
        speed: Units travelled per tick.
        state: 0 idle, 1 picking up, 2 delivering.
        orders: All orders ever assigned to this rider (history included).
        special_case: Flag for special states (e.g. blocked/queued).
        current_order: Order currently being served, or None.
        distance_travelled: Total units moved.
        log: List of event dicts with keys "event", "order_id", "time",
            "x", "y", "state".
    """

    def __init__(self, rider_id, x=SPAWN_X, y=SPAWN_Y, speed=DEFAULT_SPEED):
        """Create a rider and log its spawn.

        Args:
            rider_id: Unique rider identifier.
            x: Initial x coordinate (default 400).
            y: Initial y coordinate (default 400).
            speed: Units per tick (default 20).
        """
        self.rider_id = rider_id
        self.x = x
        self.y = y
        self.speed = speed
        self.state = IDLE
        self.orders = []
        self.special_case = False
        self.current_order = None
        self.distance_travelled = 0
        self.log = []
        self.planner = PathPlanner()
        self._record("spawn", None)

    @property
    def position(self):
        """Return the current ``(x, y)`` position."""
        return (self.x, self.y)

    @property
    def state_name(self):
        """Return a readable name for the current state."""
        return STATE_NAMES.get(self.state, "unknown")

    def active_orders(self):
        """Return orders assigned to this rider and not yet completed.

        Returns:
            list[Order]: Active orders in assignment order.
        """
        return [o for o in self.orders if o.status in (ASSIGNED, PICKED_UP)]

    def has_active_orders(self):
        """Return True if the rider has at least one active order."""
        return bool(self.active_orders())

    def _now(self):
        """Return the current simulated tick."""
        return globalvar.get_value("tick") or 0

    def _record(self, event, order_id):
        """Append an event entry to the rider log.

        Args:
            event: Event name.
            order_id: Related order id, or None.
        """
        self.log.append({
            "event": event,
            "order_id": order_id,
            "time": self._now(),
            "x": self.x,
            "y": self.y,
            "state": self.state_name,
        })

    def _start_next_order(self):
        """Begin serving the next assigned order, if any.

        Returns:
            bool: True if a new order was accepted, False if the rider is idle.
        """
        next_order = next((o for o in self.orders if o.status == ASSIGNED),
                          None)
        if next_order is None:
            self.current_order = None
            self.state = IDLE
            return False
        self.current_order = next_order
        self.state = PICKING_UP
        self._record("accepted_order", next_order.id)
        logger.info("Rider #%d accepted order #%d", self.rider_id,
                    next_order.id)
        return True

    def move(self):
        """Advance the rider by one tick.

        Handles the transitions Idle -> Picking Up (order accepted),
        Picking Up -> Delivering (arrived at restaurant) and
        Delivering -> Picking Up/Idle (order delivered).

        Returns:
            None
        """
        if self.current_order is None and not self._start_next_order():
            return
        order = self.current_order
        if self.state == PICKING_UP:
            target = order.res_pos
        else:
            target = order.cus_pos
        previous = (self.x, self.y)
        self.x, self.y = self.planner.next_step(
            self.x, self.y, target[0], target[1], self.speed)
        self.distance_travelled += (abs(self.x - previous[0])
                                    + abs(self.y - previous[1]))
        if (self.x, self.y) != target:
            return
        now = self._now()
        if self.state == PICKING_UP:
            order.mark_picked_up(now)
            self.state = DELIVERING
            self._record("arrived_at_merchant", order.id)
        else:
            order.mark_completed(now)
            self._record("delivered_to_customer", order.id)
            self.current_order = None
            self._start_next_order()

    def to_dict(self):
        """Serialise the rider to a JSON-compatible dictionary.

        Returns:
            dict: Rider fields, order id references and event log.
        """
        return {
            "rider_id": self.rider_id,
            "x": self.x,
            "y": self.y,
            "speed": self.speed,
            "state": self.state,
            "special_case": self.special_case,
            "distance_travelled": self.distance_travelled,
            "order_ids": [o.id for o in self.orders],
            "current_order_id": (self.current_order.id
                                 if self.current_order else None),
            "log": self.log,
        }

    @classmethod
    def from_dict(cls, data, orders_by_id):
        """Rebuild a rider from :meth:`to_dict` output.

        Args:
            data: Dictionary produced by :meth:`to_dict`.
            orders_by_id: Mapping of order id to restored Order objects.

        Returns:
            Rider: Restored rider.
        """
        rider = cls(data["rider_id"], data["x"], data["y"], data["speed"])
        rider.state = data.get("state", IDLE)
        rider.special_case = data.get("special_case", False)
        rider.distance_travelled = data.get("distance_travelled", 0)
        rider.orders = [orders_by_id[i] for i in data.get("order_ids", [])
                        if i in orders_by_id]
        current_id = data.get("current_order_id")
        rider.current_order = orders_by_id.get(current_id)
        rider.log = list(data.get("log", []))
        return rider
