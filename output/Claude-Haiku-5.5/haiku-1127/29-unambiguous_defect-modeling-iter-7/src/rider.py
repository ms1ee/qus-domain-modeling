"""Rider model: state machine, movement and order execution."""

import logging
import random

import globalvar
from grid import Grid
from path_planner import PathPlanner

LOGGER = logging.getLogger(__name__)

DEFAULT_SPEED = 20
STATE_IDLE = 0
STATE_PICKING_UP = 1
STATE_DELIVERING = 2
STATE_NAMES = {
    STATE_IDLE: "idle",
    STATE_PICKING_UP: "picking up",
    STATE_DELIVERING: "delivering",
}
MAX_LOG_ENTRIES = 10000

_GRID = Grid()
_PLANNER = PathPlanner(_GRID)


def _current_tick() -> int:
    """Return the simulated clock value from the global store.

    Returns:
        int: Current tick.
    """
    return int(globalvar.get_value("current_tick", 0) or 0)


class Rider:
    """A delivery rider that moves on the street network and executes orders.

    Attributes:
        rider_id: Unique identifier.
        x: Current X coordinate.
        y: Current Y coordinate.
        speed: Movement speed in units per tick.
        state: 0 idle, 1 picking up, 2 delivering.
        orders: Assigned orders; the first entry is the active order.
        special_case: True while travelling directly above/below the target.
        log: Chronological status-change records. Each entry has the keys
            ``event`` and ``order_id`` plus tick, position and state details.
    """

    def __init__(self, rider_id: int) -> None:
        """Create a rider on a random street point.

        Args:
            rider_id: Unique identifier assigned by the system.
        """
        self.rider_id = int(rider_id)
        self.x, self.y = random.choice(_GRID.road_points())
        self.speed = DEFAULT_SPEED
        self.state = STATE_IDLE
        self.orders = []
        self.special_case = False
        self.log = []
        self._record("spawn", None)

    @property
    def position(self):
        """Return the current position.

        Returns:
            Tuple[int, int]: (x, y).
        """
        return self.x, self.y

    @property
    def state_name(self) -> str:
        """Return a human readable state name.

        Returns:
            str: Name of the current state.
        """
        return STATE_NAMES.get(self.state, "unknown")

    @property
    def is_idle(self) -> bool:
        """Return True when the rider can accept a new order.

        Returns:
            bool: Idle state with no assigned orders.
        """
        return self.state == STATE_IDLE and not self.orders

    def _record(self, event: str, order_id) -> None:
        """Append a status change entry to the rider log.

        Args:
            event: Event name such as ``"accepted_order"``.
            order_id: Related order identifier, or None.

        Returns:
            None
        """
        self.log.append(
            {
                "event": event,
                "order_id": order_id,
                "tick": _current_tick(),
                "rider_id": self.rider_id,
                "x": self.x,
                "y": self.y,
                "state": self.state,
            }
        )
        if len(self.log) > MAX_LOG_ENTRIES:
            del self.log[: len(self.log) - MAX_LOG_ENTRIES]

    def _advance(self, target) -> bool:
        """Move one tick toward a target along the streets.

        Args:
            target: Destination (x, y).

        Returns:
            bool: True if the rider reached the target this tick.
        """
        tx, ty = target
        nx, ny, arrived = _PLANNER.next_step(self.x, self.y, tx, ty, self.speed)
        self.x, self.y = nx, ny
        self.special_case = nx == tx and ny != ty
        return arrived

    def _begin_order(self, order) -> None:
        """Start working on the given order (idle -> picking up).

        Args:
            order: The order to start.

        Returns:
            None
        """
        self.state = STATE_PICKING_UP
        self.special_case = False
        order.mark_picking_up()
        self._record("accepted_order", order.id)

    def _recover(self) -> None:
        """Restore a consistent state after an unexpected error.

        Returns:
            None
        """
        if not self.orders:
            self.state = STATE_IDLE
            self.special_case = False
        elif self.state == STATE_IDLE:
            self._begin_order(self.orders[0])

    def move(self) -> None:
        """Advance this rider by one tick, handling state transitions.

        Transitions:
            idle -> picking up when an order is present;
            picking up -> delivering on arrival at the restaurant;
            delivering -> idle (or picking up the next order) on delivery.

        Returns:
            None
        """
        try:
            self._advance_state()
        except Exception:  # pragma: no cover - defensive recovery path
            LOGGER.exception("Rider %s failed during move; recovering", self.rider_id)
            self._recover()

    def _advance_state(self) -> None:
        """Perform the state machine step for one tick.

        Returns:
            None
        """
        if not self.orders:
            if self.state != STATE_IDLE:
                self.state = STATE_IDLE
                self.special_case = False
            return

        if self.state == STATE_IDLE:
            self._begin_order(self.orders[0])

        if self.state == STATE_PICKING_UP:
            order = self.orders[0]
            if self._advance(order.res_pos):
                self.state = STATE_DELIVERING
                order.mark_delivering()
                self._record("arrived_at_merchant", order.id)
            return

        if self.state == STATE_DELIVERING:
            order = self.orders[0]
            if self._advance(order.cus_pos):
                order.complete(_current_tick())
                self.orders.pop(0)
                self._record("delivered_to_customer", order.id)
                self.special_case = False
                if self.orders:
                    self._begin_order(self.orders[0])
                else:
                    self.state = STATE_IDLE

    def to_dict(self) -> dict:
        """Serialize the rider to a JSON-compatible dictionary.

        Returns:
            dict: Rider attributes and order identifiers.
        """
        return {
            "rider_id": self.rider_id,
            "x": self.x,
            "y": self.y,
            "speed": self.speed,
            "state": self.state,
            "state_name": self.state_name,
            "special_case": self.special_case,
            "orders": [order.id for order in self.orders],
            "log": list(self.log),
        }
