"""Rider model: state machine, movement and order handling.

Rider states:
    0 (IDLE): available for new orders.
    1 (PICKING_UP): en route to the restaurant.
    2 (DELIVERING): en route to the customer.

Orders are assigned by appending them to ``rider.orders``. The state
transitions and their log entries happen inside ``move()``.
"""

import logging

from globalvar import get_value
from path_planner import PathPlanner

logger = logging.getLogger(__name__)

IDLE = 0
PICKING_UP = 1
DELIVERING = 2

STATE_NAMES = {IDLE: "idle", PICKING_UP: "picking up", DELIVERING: "delivering"}

DEFAULT_RIDER_X = 435
DEFAULT_RIDER_Y = 385
DEFAULT_SPEED = 10


def _current_tick() -> int:
    """Return the current simulated tick (0 if unavailable)."""
    value = get_value("tick")
    return value if isinstance(value, int) else 0


class Rider:
    """A delivery rider that moves on the street grid and serves orders.

    Attributes:
        rider_id: Unique identifier.
        x, y: Current coordinates in units.
        speed: Distance covered per tick (units/tick).
        state: Current status (0 idle, 1 picking up, 2 delivering).
        orders: List of assigned Order objects (first one is active).
        special_case: Flag set when the rider is directly above/below its
            target or is waiting for a higher-priority rider to pass.
        log: List of event dictionaries with keys "event", "order_id",
            "tick", "x", "y", "state".
    """

    def __init__(self, rider_id: int) -> None:
        """Create a rider at the default starting position.

        Args:
            rider_id: Unique identifier of the rider.
        """
        self.rider_id = rider_id
        self.x = DEFAULT_RIDER_X
        self.y = DEFAULT_RIDER_Y
        self.speed = DEFAULT_SPEED
        self.state = IDLE
        self.orders = []
        self.special_case = False
        self.log = []
        self.planner = PathPlanner()
        self.log_event("spawn", None)

    @property
    def position(self) -> tuple:
        """Current (x, y) position."""
        return (self.x, self.y)

    def current_order(self):
        """Return the order currently being served, or None."""
        return self.orders[0] if self.orders else None

    def log_event(self, event: str, order_id):
        """Append a status-change record to the rider log.

        Args:
            event: Event name ("spawn", "accepted_order",
                "arrived_at_merchant" or "delivered_to_customer").
            order_id: Related order identifier, or None.

        Returns:
            The created log entry dictionary.
        """
        entry = {
            "event": event,
            "order_id": order_id,
            "tick": _current_tick(),
            "x": self.x,
            "y": self.y,
            "state": self.state,
        }
        self.log.append(entry)
        logger.debug("Rider %d: %s order=%s", self.rider_id, event, order_id)
        return entry

    def move(self) -> None:
        """Advance the rider by one tick.

        Handles idle → picking up → delivering → idle transitions, moves the
        rider up to ``speed`` units along the grid and logs key events.
        """
        order = self.current_order()
        if order is None:
            # Consistency check: no orders means the rider must be idle.
            self.state = IDLE
            self.special_case = False
            return

        if self.state == IDLE:
            self._start_pickup(order)

        if self.state == PICKING_UP:
            self._advance(order.res_pos)
            if self.position == order.res_pos:
                self.state = DELIVERING
                order.mark_picked_up(_current_tick())
                self.log_event("arrived_at_merchant", order.id)
        elif self.state == DELIVERING:
            self._advance(order.cus_pos)
            if self.position == order.cus_pos:
                order.complete(_current_tick())
                self.orders.remove(order)
                self.log_event("delivered_to_customer", order.id)
                next_order = self.current_order()
                if next_order is None:
                    self.state = IDLE
                    self.special_case = False
                else:
                    self._start_pickup(next_order)
        else:
            # Unknown state: recover to a consistent state.
            logger.warning("Rider %d had invalid state %s", self.rider_id, self.state)
            self.state = PICKING_UP

    def _start_pickup(self, order) -> None:
        """Begin serving an order: switch to picking up and log acceptance."""
        self.state = PICKING_UP
        order.status = "picking_up"
        self.log_event("accepted_order", order.id)

    def _advance(self, target: tuple) -> None:
        """Move up to ``speed`` unit steps toward ``target``.

        Deadlock/conflict avoidance: a rider yields when the next cell is
        occupied by a rider with a lower ID. Lower IDs never yield, so the
        scheme cannot deadlock.

        Args:
            target: (x, y) destination point.
        """
        tx, ty = target
        self.special_case = self.x == tx and self.y != ty
        budget = self.speed
        while budget > 0 and self.position != (tx, ty):
            nx, ny = self.planner.next_step(self.x, self.y, tx, ty)
            if self._blocked(nx, ny):
                self.special_case = True
                break
            self.x, self.y = nx, ny
            budget -= 1

    def _blocked(self, x: int, y: int) -> bool:
        """Return True if a higher-priority rider occupies (x, y)."""
        for other in get_value("riders") or []:
            if other is self:
                continue
            if other.rider_id < self.rider_id and other.position == (x, y):
                return True
        return False

    def __repr__(self) -> str:
        return (
            f"Rider(id={self.rider_id}, pos=({self.x}, {self.y}), "
            f"state={STATE_NAMES.get(self.state, self.state)}, orders={len(self.orders)})"
        )
