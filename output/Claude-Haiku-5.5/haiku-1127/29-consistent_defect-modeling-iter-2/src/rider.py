"""Rider model: state machine, movement and delivery log."""

import logging

import globalvar
from path_planner import PathPlanner

logger = logging.getLogger(__name__)

STATE_IDLE = 0
STATE_PICKING_UP = 1
STATE_DELIVERING = 2
STATE_NAMES = {
    STATE_IDLE: "idle",
    STATE_PICKING_UP: "picking up",
    STATE_DELIVERING: "delivering",
}

DEFAULT_SPEED = 20
START_X = 400
START_Y = 400

_planner = PathPlanner()


def _current_tick():
    """Return the simulated time stored in the global table."""
    return globalvar.get_value("tick") or 0


class Rider:
    """A delivery rider.

    Attributes:
        rider_id: Unique integer identifier.
        x, y: Current coordinates.
        speed: Movement speed in units per tick.
        state: 0 = idle, 1 = picking up, 2 = delivering.
        orders: All orders assigned to this rider (including history).
        special_case: True while directly above/below the current target.
        current_order: The order currently being executed, or None.
        log: List of event dicts with keys ``event`` and ``order_id``
            (plus ``tick``, ``x``, ``y`` and ``state`` for display).
    """

    def __init__(self, rider_id):
        """Create a rider at the default start location, logging a spawn.

        Args:
            rider_id: Unique positive integer identifier.

        Raises:
            ValueError: If ``rider_id`` is not a positive integer.
        """
        if not isinstance(rider_id, int) or isinstance(rider_id, bool):
            raise ValueError("rider_id must be an integer")
        if rider_id < 1:
            raise ValueError("rider_id must be positive")
        self.rider_id = rider_id
        self.x = START_X
        self.y = START_Y
        self.speed = DEFAULT_SPEED
        self.state = STATE_IDLE
        self.orders = []
        self.special_case = False
        self.current_order = None
        self.log = []
        self._record("spawn", None)
        logger.info("Rider %d spawned at (%d, %d)", rider_id, self.x, self.y)

    def _record(self, event, order_id):
        """Append an entry to the rider's event log."""
        self.log.append({
            "event": event,
            "order_id": order_id,
            "tick": _current_tick(),
            "x": self.x,
            "y": self.y,
            "state": self.state,
        })

    def active_orders(self):
        """Return orders that are not yet completed."""
        return [o for o in self.orders if o.status != "completed"]

    def assigned_orders(self):
        """Return orders assigned to this rider that have not been accepted."""
        return [o for o in self.orders if o.status == "assigned"]

    def is_idle(self):
        """Return True if the rider has no work at all."""
        return self.state == STATE_IDLE and not self.assigned_orders()

    def _next_assigned_order(self):
        """Return the earliest assigned-but-not-accepted order, or None."""
        pending = self.assigned_orders()
        return pending[0] if pending else None

    def _accept_order(self, order):
        """Start working on ``order`` (idle/delivering -> picking up)."""
        self.state = STATE_PICKING_UP
        self.current_order = order
        order.mark_picking_up()
        self._record("accepted_order", order.order_id)
        logger.debug("Rider %d accepted order %d", self.rider_id, order.order_id)

    def _arrive_at_merchant(self, order):
        """Handle arrival at the restaurant (picking up -> delivering)."""
        self.state = STATE_DELIVERING
        order.mark_delivering()
        self._record("arrived_at_merchant", order.order_id)

    def _deliver(self, order):
        """Handle delivery to the customer and pick up the next order if any."""
        order.complete(_current_tick())
        self._record("delivered_to_customer", order.order_id)
        self.current_order = None
        nxt = self._next_assigned_order()
        if nxt is not None:
            self._accept_order(nxt)
        else:
            self.state = STATE_IDLE
            self.special_case = False

    def move(self):
        """Advance the rider by one tick.

        Performs the idle -> picking up transition when an order is waiting,
        moves along the street grid, and applies arrival transitions.

        Returns:
            True if the rider performed a movement step, False otherwise.
        """
        if self.state == STATE_IDLE:
            nxt = self._next_assigned_order()
            if nxt is None:
                return False
            self._accept_order(nxt)

        order = self.current_order
        if order is None:
            logger.error("Rider %d has no current order; recovering",
                         self.rider_id)
            self.recover()
            return False

        target = order.res_pos if self.state == STATE_PICKING_UP else order.cus_pos
        self.x, self.y, self.special_case = _planner.next_position(
            self.x, self.y, target[0], target[1], self.speed
        )
        if (self.x, self.y) == tuple(target):
            if self.state == STATE_PICKING_UP:
                self._arrive_at_merchant(order)
            else:
                self._deliver(order)
        return True

    def recover(self):
        """Restore a consistent state after an exceptional condition.

        The interrupted order is re-queued as ``assigned`` so it will be
        picked up again, and the rider becomes idle.
        """
        order = self.current_order
        order_id = None
        if order is not None and order.status != "completed":
            order.status = "assigned"
            order_id = order.order_id
        self.current_order = None
        self.state = STATE_IDLE
        self.special_case = False
        self._record("recovered", order_id)
        logger.warning("Rider %d recovered to idle", self.rider_id)

    def to_dict(self):
        """Return a JSON-serialisable snapshot of the rider."""
        return {
            "rider_id": self.rider_id,
            "x": self.x,
            "y": self.y,
            "speed": self.speed,
            "state": self.state,
            "special_case": self.special_case,
            "orders": [o.to_dict() for o in self.orders],
            "log": list(self.log),
        }
