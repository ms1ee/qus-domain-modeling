"""Rider model: state machine, street movement and event logging."""

import logging

import globalvar
from grid import INTERSECTIONS
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

DEFAULT_SPEEDS = (10, 15, 20)
MAX_LOG_ENTRIES = 5000
_SPAWN_STRIDE = 13  # coprime with the 81 intersections, spreads riders out

_PLANNER = PathPlanner()


def _current_tick():
    """Return the current simulated tick from the global store."""
    tick = globalvar.get_value("current_tick", 0)
    return int(tick) if tick is not None else 0


def _spawn_point(rider_id):
    """Return a deterministic starting intersection (always on a road)."""
    return INTERSECTIONS[(rider_id * _SPAWN_STRIDE) % len(INTERSECTIONS)]


class Rider:
    """A delivery rider that moves along streets and serves assigned orders.

    Orders are assigned by appending them to ``orders``. The first order in
    the list is the active one. ``move()`` advances the rider by one tick and
    performs all state transitions and their log entries.

    Attributes:
        rider_id (int): Unique identifier.
        x (int), y (int): Current position on the street grid.
        speed (int): Units travelled per tick.
        state (int): 0 idle, 1 picking up, 2 delivering.
        orders (list[Order]): Assigned orders, active order first.
        special_case (bool): True while directly above or below the target.
        path (list[tuple]): Remaining unit-step points of the current leg.
        log (list[dict]): Status change entries with keys "event" and
            "order_id" (plus time, rider_id, position, state, description).
    """

    def __init__(self, rider_id):
        """Create a rider at a deterministic street intersection.

        Args:
            rider_id: Unique positive integer identifier.
        """
        self.rider_id = int(rider_id)
        self.x, self.y = _spawn_point(self.rider_id)
        speeds = tuple(globalvar.get_value("speed_options") or DEFAULT_SPEEDS)
        self.speed = int(speeds[(self.rider_id - 1) % len(speeds)])
        self.state = IDLE
        self.orders = []
        self.special_case = False
        self.path = []
        self.log = []
        self._record("spawn", None, "rider recruited")

    @property
    def position(self):
        """Return the current position as a tuple (x, y)."""
        return (self.x, self.y)

    @property
    def state_name(self):
        """Return the human-readable name of the current state."""
        return STATE_NAMES[self.state]

    def _record(self, event, order_id, description=""):
        """Append a status change entry to the rider log.

        Args:
            event: Event name, e.g. "accepted_order".
            order_id: Related order id, or None.
            description: Optional free text.

        Returns:
            dict: The created log entry.
        """
        entry = {
            "time": _current_tick(),
            "event": event,
            "order_id": order_id,
            "rider_id": self.rider_id,
            "x": self.x,
            "y": self.y,
            "state": self.state,
            "description": description,
        }
        self.log.append(entry)
        if len(self.log) > MAX_LOG_ENTRIES:
            del self.log[:len(self.log) - MAX_LOG_ENTRIES]
        logger.debug("rider %s event=%s order=%s", self.rider_id, event, order_id)
        return entry

    def move(self):
        """Advance the rider by one tick.

        Handles idle-to-picking-up when an order is present, moves along the
        street route toward the restaurant or customer, and performs the
        arrival transitions (picking up to delivering, delivering to idle).
        """
        tick = _current_tick()
        if not self.orders:
            if self.state != IDLE:
                logger.warning("rider %s had no orders while state=%s; resetting",
                               self.rider_id, self.state)
                self.state = IDLE
                self.path = []
            return

        if self.state == IDLE:
            self.state = PICKING_UP
            self.path = []
            order = self.orders[0]
            self._record("accepted_order", order.id,
                         "accepted order, heading to restaurant %r" % (order.restaurant_pos,))

        order = self.orders[0]
        target = order.restaurant_pos if self.state == PICKING_UP else order.customer_pos
        if self.position != target:
            self._step_towards(order, target)
        if self.position == target:
            self._arrive(order, tick)

    def _step_towards(self, order, target):
        """Move up to ``speed`` unit steps along the street route to ``target``.

        Args:
            order: The active order whose distance counter is updated.
            target: Destination tuple (x, y).
        """
        if not self.path:
            self.path = _PLANNER.plan(self.position, target)
            # Directly above or below the target: straight-line special case.
            self.special_case = self.x == target[0] and self.y != target[1]
        if not self.path:
            return
        steps = min(self.speed, len(self.path))
        travelled = self.path[:steps]
        del self.path[:steps]
        self.x, self.y = travelled[-1]
        order.distance += steps

    def _arrive(self, order, tick):
        """Apply the state transition for reaching the current target.

        Args:
            order: The active order.
            tick: Current simulated tick.
        """
        self.path = []
        self.special_case = False
        if self.state == PICKING_UP:
            self.state = DELIVERING
            order.mark_picked_up(tick)
            self._record("arrived_at_merchant", order.id,
                         "picked up at restaurant %r" % (order.restaurant_pos,))
        elif self.state == DELIVERING:
            self.orders.remove(order)
            order.complete(tick)
            self.state = IDLE
            self._record("delivered_to_customer", order.id,
                         "delivered to customer %r" % (order.customer_pos,))

    def to_dict(self):
        """Return a JSON-serialisable snapshot of the rider.

        Returns:
            dict: Rider attributes including assigned order ids.
        """
        return {
            "rider_id": self.rider_id,
            "x": self.x,
            "y": self.y,
            "speed": self.speed,
            "state": self.state,
            "orders": [order.id for order in self.orders],
            "special_case": self.special_case,
        }
