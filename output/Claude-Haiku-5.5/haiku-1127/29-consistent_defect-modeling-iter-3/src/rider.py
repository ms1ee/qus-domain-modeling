"""Rider model: movement, state transitions and delivery event logging.

Rider states:
    0 (STATE_IDLE): available for new orders.
    1 (STATE_PICKING_UP): travelling to the restaurant of the current order.
    2 (STATE_DELIVERING): travelling to the customer with the picked-up order.

Log events recorded in ``Rider.log``:
    "spawn", "accepted_order", "arrived_at_merchant", "delivered_to_customer".
"""

import logging

import globalvar
from path_planner import PathPlanner

logger = logging.getLogger(__name__)

RIDER_SPEED = 20
START_X = 400
START_Y = 400

STATE_IDLE = 0
STATE_PICKING_UP = 1
STATE_DELIVERING = 2
STATE_NAMES = {
    STATE_IDLE: "idle",
    STATE_PICKING_UP: "picking up",
    STATE_DELIVERING: "delivering",
}

PICKUP_STATUSES = ("accepted", "picking_up")
DELIVERY_STATUSES = ("delivering",)

_planner = PathPlanner()


class Rider:
    """A delivery rider who moves on the street grid and serves orders.

    Attributes:
        rider_id (int): Unique identifier.
        x (int): Current x coordinate.
        y (int): Current y coordinate.
        speed (int): Units travelled per tick (fixed at 20).
        state (int): 0 idle, 1 picking up, 2 delivering.
        orders (list[Order]): Assigned orders, including completed history.
        special_case (bool): True while the rider is level with its target
            on one axis (directly above, below, left or right of it).
        log (list[dict]): Status change records with keys "event",
            "order_id", "tick", "x", "y" and "state".
    """

    def __init__(self, rider_id):
        """Create a rider at the default start position (400, 400).

        Args:
            rider_id: Unique integer identifier.
        """
        self.rider_id = int(rider_id)
        self.x = START_X
        self.y = START_Y
        self.speed = RIDER_SPEED
        self.state = STATE_IDLE
        self.orders = []
        self.special_case = False
        self.log = []
        self._record("spawn")

    @property
    def state_name(self):
        """Human-readable name of the current state."""
        return STATE_NAMES.get(self.state, "unknown")

    @property
    def position(self):
        """Current ``(x, y)`` position."""
        return (self.x, self.y)

    def active_orders(self):
        """Return orders that have not been completed yet."""
        return [order for order in self.orders if order.status != "completed"]

    def accept_pending_orders(self):
        """Accept newly assigned orders and update the rider state.

        Orders that were appended to ``orders`` but not yet accepted are
        marked as accepted and an "accepted_order" event is logged. An idle
        rider with work transitions to the picking-up state.
        """
        for order in self.orders:
            if order.status in ("pending", "assigned"):
                order.status = "accepted"
                order.rider_id = self.rider_id
                self._record("accepted_order", order.id)
        if self.state == STATE_IDLE and self._find_order(PICKUP_STATUSES):
            self.state = STATE_PICKING_UP

    def move(self):
        """Advance the rider by one tick.

        Handles order acceptance, movement toward the current target and the
        state transitions on arrival at the restaurant and at the customer.
        """
        self.accept_pending_orders()
        if self.state == STATE_IDLE:
            return
        if self.state == STATE_PICKING_UP:
            self._move_to_restaurant()
        elif self.state == STATE_DELIVERING:
            self._move_to_customer()

    def to_dict(self):
        """Return a JSON-serialisable representation of the rider."""
        return {
            "rider_id": self.rider_id,
            "x": self.x,
            "y": self.y,
            "speed": self.speed,
            "state": self.state,
            "special_case": self.special_case,
            "order_ids": [order.id for order in self.orders],
            "log": self.log,
        }

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------
    def _move_to_restaurant(self):
        """Move toward the restaurant of the next order awaiting pickup."""
        order = self._find_order(PICKUP_STATUSES)
        if order is None:
            self._resync_state()
            return
        order.status = "picking_up"
        self._step(order.res_pos)
        if self._at(order.res_pos):
            order.status = "delivering"
            self.state = STATE_DELIVERING
            self.special_case = False
            self._record("arrived_at_merchant", order.id)

    def _move_to_customer(self):
        """Move toward the customer of the order currently being delivered."""
        order = self._find_order(DELIVERY_STATUSES)
        if order is None:
            self._resync_state()
            return
        self._step(order.cus_pos)
        if self._at(order.cus_pos):
            tick = globalvar.get_value("current_tick", 0)
            order.complete(tick)
            self._resync_state()
            self._record("delivered_to_customer", order.id)

    def _resync_state(self):
        """Set the state from the statuses of the orders held."""
        if self._find_order(DELIVERY_STATUSES):
            self.state = STATE_DELIVERING
        elif self._find_order(PICKUP_STATUSES):
            self.state = STATE_PICKING_UP
        else:
            self.state = STATE_IDLE
            self.special_case = False

    def _find_order(self, statuses):
        """Return the first order (in assignment order) with a matching status."""
        for order in self.orders:
            if order.status in statuses:
                return order
        return None

    def _step(self, target):
        """Move one tick toward ``target`` along the street grid."""
        tx, ty = target
        self.x, self.y = _planner.next_position((self.x, self.y), (tx, ty), self.speed)
        # Special case: exactly one axis aligned with the target (same street).
        self.special_case = (self.x == tx) != (self.y == ty)

    def _at(self, target):
        """Return True when the rider stands exactly on ``target``."""
        return (self.x, self.y) == (target[0], target[1])

    def _record(self, event, order_id=None):
        """Append a status change record to the rider log."""
        entry = {
            "event": event,
            "order_id": order_id,
            "tick": globalvar.get_value("current_tick", 0),
            "x": self.x,
            "y": self.y,
            "state": self.state,
        }
        self.log.append(entry)
        logger.debug("rider=%s event=%s order=%s", self.rider_id, event, order_id)
