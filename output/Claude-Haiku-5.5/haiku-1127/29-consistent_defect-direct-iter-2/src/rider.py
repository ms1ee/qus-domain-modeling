"""Rider model: state transitions, movement and event logging."""

import logging
from typing import Any, Dict, List, Optional, Sequence, Tuple

import globalvar
from path_planner import PathPlanner

logger = logging.getLogger(__name__)

RIDER_SPEED = 20
SPAWN_X = 400
SPAWN_Y = 400


class Rider:
    """A delivery rider that moves on the street grid and serves orders.

    State values:
        0 (IDLE): available for new orders.
        1 (PICKING_UP): en route to the restaurant.
        2 (DELIVERING): en route to the customer.

    Log entries (``rider.log``) are dicts with at least the keys
    ``"event"`` and ``"order_id"``. Events are ``"spawn"``,
    ``"accepted_order"``, ``"arrived_at_merchant"`` and
    ``"delivered_to_customer"``.
    """

    IDLE = 0
    PICKING_UP = 1
    DELIVERING = 2
    STATE_NAMES = {0: "idle", 1: "picking up", 2: "delivering"}

    def __init__(self, rider_id: int) -> None:
        """Create a rider at the spawn point, idle, with no orders.

        Args:
            rider_id: Unique identifier of the rider.
        """
        self.rider_id: int = int(rider_id)
        self.x: int = SPAWN_X
        self.y: int = SPAWN_Y
        self.speed: int = RIDER_SPEED
        self.state: int = self.IDLE
        self.orders: List[Any] = []
        self.special_case: bool = False
        self.log: List[Dict[str, Any]] = []
        self._record("spawn", None)

    @property
    def position(self) -> Tuple[int, int]:
        """Current ``(x, y)`` position."""
        return self.x, self.y

    @property
    def state_name(self) -> str:
        """Human-readable name of the current state."""
        return self.STATE_NAMES.get(self.state, "unknown")

    def active_orders(self) -> List[Any]:
        """Return orders assigned to this rider that are not yet completed.

        Returns:
            List of active :class:`order_model.Order` objects in FIFO order.
        """
        return [o for o in self.orders if o.status != "completed"]

    def current_order(self) -> Optional[Any]:
        """Return the order currently being served, if any.

        Returns:
            The first active order, or None.
        """
        active = self.active_orders()
        return active[0] if active else None

    def _now(self) -> int:
        """Return the current simulated tick."""
        return globalvar.get_value("tick", 0) or 0

    def _record(self, event: str, order_id: Optional[int]) -> None:
        """Append an event entry to the rider's log.

        Args:
            event: Event name.
            order_id: Related order ID, or None.
        """
        entry = {
            "event": event,
            "order_id": order_id,
            "rider_id": self.rider_id,
            "time": self._now(),
            "x": self.x,
            "y": self.y,
            "state": self.state,
        }
        self.log.append(entry)
        logger.debug("Rider %s: %s order=%s", self.rider_id, event, order_id)

    def _advance(self, target: Sequence[int]) -> bool:
        """Move one tick towards a target along the street grid.

        Args:
            target: Destination coordinate.

        Returns:
            True if the rider is at the target after this movement.
        """
        tx, ty = int(target[0]), int(target[1])
        if (self.x, self.y) == (tx, ty):
            self.special_case = False
            return True
        nx, ny, special = PathPlanner.next_position(
            self.x, self.y, tx, ty, self.speed)
        self.x, self.y = nx, ny
        self.special_case = special
        return (nx, ny) == (tx, ty)

    def move(self) -> None:
        """Advance the rider by one tick.

        Performs state transitions and records log entries:
            * Idle -> Picking Up when an order is assigned ("accepted_order").
            * Picking Up -> Delivering on reaching the restaurant
              ("arrived_at_merchant").
            * Delivering -> Picking Up (or Idle) on delivering to the
              customer ("delivered_to_customer").
        """
        order = self.current_order()
        if order is None:
            if self.state != self.IDLE:
                self.state = self.IDLE
                self.special_case = False
            return

        if self.state == self.IDLE:
            self.state = self.PICKING_UP
            self._record("accepted_order", order.id)

        if self.state == self.PICKING_UP:
            if self._advance(order.res_pos):
                order.mark_picked_up()
                self.state = self.DELIVERING
                self._record("arrived_at_merchant", order.id)
            return

        if self.state == self.DELIVERING:
            if self._advance(order.cus_pos):
                order.mark_completed(self._now())
                self._record("delivered_to_customer", order.id)
                next_order = self.current_order()
                if next_order is not None:
                    self._record("accepted_order", next_order.id)
                    self.state = self.PICKING_UP
                else:
                    self.state = self.IDLE
                    self.special_case = False

    def to_dict(self) -> Dict[str, Any]:
        """Serialize the rider to a JSON-compatible dictionary.

        Returns:
            Dictionary representation of the rider and its log.
        """
        return {
            "rider_id": self.rider_id,
            "x": self.x,
            "y": self.y,
            "speed": self.speed,
            "state": self.state,
            "special_case": self.special_case,
            "order_ids": [o.id for o in self.orders],
            "log": list(self.log),
        }
