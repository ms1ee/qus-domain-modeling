"""Rider model: state machine, street-based movement and event logging."""

import logging
from collections import deque

import globalvar
from path_planner import plan_path

logger = logging.getLogger(__name__)

STATE_IDLE = 0
STATE_PICKING_UP = 1
STATE_DELIVERING = 2

START_X = 435
START_Y = 385
DEFAULT_SPEED = 10


def _current_tick():
    """Return the simulation tick stored in the global variables."""
    return globalvar.get_value("current_tick", 0) or 0


class Rider:
    """A delivery rider that moves on the street grid and serves orders.

    Attributes:
        rider_id: Unique identifier.
        x: Current x coordinate.
        y: Current y coordinate.
        speed: Movement speed in units per tick.
        state: 0 = idle, 1 = picking up, 2 = delivering.
        orders: List of assigned orders; ``orders[0]`` is the active order.
        special_case: True when the rider is directly above or below its target.
        log: List of event dictionaries with keys ``event`` and ``order_id``
            (plus ``tick``, ``rider_id``, ``x``, ``y``, ``state``).
        distance_travelled: Total units moved so far.
    """

    def __init__(self, rider_id):
        """Create a rider at the default start position.

        Args:
            rider_id: Unique integer identifier.
        """
        self.rider_id = int(rider_id)
        self.x = START_X
        self.y = START_Y
        self.speed = DEFAULT_SPEED
        self.state = STATE_IDLE
        self.orders = []
        self.special_case = False
        self.log = []
        self.distance_travelled = 0
        self._accepted_ids = set()
        self._path = deque()
        self._path_key = None
        self._record("spawn", None)

    def _record(self, event, order_id):
        """Append an event entry to the rider log."""
        entry = {
            "event": event,
            "order_id": order_id,
            "tick": _current_tick(),
            "rider_id": self.rider_id,
            "x": self.x,
            "y": self.y,
            "state": self.state,
        }
        self.log.append(entry)
        logger.debug("Rider %d event=%s order=%s", self.rider_id, event, order_id)

    def _reset_route(self):
        """Discard the currently planned route."""
        self._path.clear()
        self._path_key = None

    def _accept_new_orders(self):
        """Detect newly assigned orders and move idle riders into pickup."""
        for order in self.orders:
            if order.id in self._accepted_ids:
                continue
            self._accepted_ids.add(order.id)
            if self.state == STATE_IDLE:
                self.state = STATE_PICKING_UP
            self._record("accepted_order", order.id)

    def _plan_route(self, target, key):
        """Plan a route to ``target`` and update the special-case flag.

        Args:
            target: ``(x, y)`` destination.
            key: ``(order_id, state)`` identifying the leg being planned.
        """
        tx, ty = target
        self._path = deque(plan_path(self.x, self.y, tx, ty))
        self._path_key = key
        # Special case: rider directly above or below the target.
        self.special_case = self.x == tx

    def _arrive(self, order):
        """Handle arrival at the current leg's destination.

        Arriving at the restaurant switches the rider to delivering. Arriving
        at the customer completes the order, removes it from the rider's list
        and releases the rider to idle (or to the next pending pickup).

        Args:
            order: The active order (``orders[0]``).
        """
        self._reset_route()
        if self.state == STATE_PICKING_UP:
            self.state = STATE_DELIVERING
            self._record("arrived_at_merchant", order.id)
        elif self.state == STATE_DELIVERING:
            order.complete(_current_tick())
            self.orders.pop(0)
            self._accepted_ids.discard(order.id)
            self.state = STATE_PICKING_UP if self.orders else STATE_IDLE
            self.special_case = False
            self._record("delivered_to_customer", order.id)

    def check_consistency(self):
        """Repair inconsistent state between ``state`` and ``orders``.

        Returns:
            True if a repair was made, False otherwise.
        """
        repaired = False
        if not self.orders:
            if self.state != STATE_IDLE:
                logger.warning("Rider %d had state %d without orders; resetting to idle.",
                               self.rider_id, self.state)
                self.state = STATE_IDLE
                repaired = True
            self._reset_route()
            self.special_case = False
        elif self.state == STATE_IDLE:
            logger.warning("Rider %d had orders while idle; resuming pickup.", self.rider_id)
            self.state = STATE_PICKING_UP
            repaired = True
        return repaired

    def move(self):
        """Advance the rider by one tick.

        Handles acceptance of new orders, the pickup and delivery state
        transitions, and movement of up to ``speed`` units along the planned
        street route.
        """
        self._accept_new_orders()
        if not self.orders:
            self.check_consistency()
            return

        order = self.orders[0]
        if self.state == STATE_DELIVERING:
            target = order.customer
        else:
            target = order.restaurant
        key = (order.id, self.state)
        if key != self._path_key:
            self._plan_route(target, key)

        for _ in range(self.speed):
            if not self._path:
                break
            self.x, self.y = self._path.popleft()
            self.distance_travelled += 1

        if not self._path:
            self._arrive(order)

    def to_dict(self):
        """Return a JSON-serialisable representation of the rider."""
        return {
            "rider_id": self.rider_id,
            "x": self.x,
            "y": self.y,
            "speed": self.speed,
            "state": self.state,
            "order_ids": [order.id for order in self.orders],
            "special_case": self.special_case,
            "distance_travelled": self.distance_travelled,
        }
