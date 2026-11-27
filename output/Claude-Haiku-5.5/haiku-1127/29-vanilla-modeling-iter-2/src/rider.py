"""Rider entity: state machine, movement and event logging.

State machine:
    IDLE (0) -> PICKING_UP (1) when an order is accepted;
    PICKING_UP (1) -> DELIVERING (2) on arrival at the restaurant;
    DELIVERING (2) -> IDLE (0) (or PICKING_UP for a queued order) on delivery.
"""

from typing import Any, Dict, List, Optional, Set, Tuple

import globalvar
from path_planner import PathPlanner

IDLE = 0
PICKING_UP = 1
DELIVERING = 2

STATE_NAMES = {IDLE: "idle", PICKING_UP: "picking up", DELIVERING: "delivering"}


class Rider:
    """A delivery rider that moves on the grid and serves assigned orders.

    Attributes:
        rider_id: Unique identifier.
        x: Current x coordinate.
        y: Current y coordinate.
        speed: Distance covered per tick.
        state: 0 idle, 1 picking up, 2 delivering.
        orders: Assigned orders, served in order.
        special_case: True while the rider is directly above or below its target.
        log: Status change records; each entry has "event" and "order_id" keys.
        planner: Path planner used for movement.
        distance_travelled: Total distance moved.
    """

    SPAWN_X = 435
    SPAWN_Y = 385
    DEFAULT_SPEED = 10

    def __init__(self, rider_id: int, speed: int = DEFAULT_SPEED) -> None:
        """Create a rider at the spawn point in the idle state.

        Args:
            rider_id: Unique identifier.
            speed: Movement speed in units per tick.
        """
        self.rider_id = int(rider_id)
        self.x = self.SPAWN_X
        self.y = self.SPAWN_Y
        self.speed = int(speed)
        self.state = IDLE
        self.orders: List[Any] = []
        self.special_case = False
        self.log: List[Dict[str, Any]] = []
        self.planner = PathPlanner()
        self.distance_travelled = 0.0
        self._accepted_ids: Set[int] = set()
        self._record("spawn", None)

    # ------------------------------------------------------------------
    # Queries
    # ------------------------------------------------------------------
    @property
    def position(self) -> Tuple[int, int]:
        """Return the current ``(x, y)`` position."""
        return self.x, self.y

    @property
    def state_name(self) -> str:
        """Return a readable name for the current state."""
        return STATE_NAMES.get(self.state, "unknown")

    def current_target(self) -> Optional[Tuple[int, int]]:
        """Return the point the rider is heading to, or None if idle.

        Returns:
            Restaurant position while picking up, customer position while
            delivering, otherwise None.
        """
        if not self.orders:
            return None
        if self.state == PICKING_UP:
            return self.orders[0].res_pos
        if self.state == DELIVERING:
            return self.orders[0].cus_pos
        return None

    # ------------------------------------------------------------------
    # Order handling
    # ------------------------------------------------------------------
    def add_order(self, order: Any) -> None:
        """Assign an order to this rider.

        Appends the order to ``orders``, logs an "accepted_order" event and
        moves an idle rider into the picking-up state.

        Args:
            order: ``Order`` instance to assign.
        """
        if order not in self.orders:
            self.orders.append(order)
        self._sync_orders()

    def _sync_orders(self) -> None:
        """Synchronise state with the order list.

        Logs "accepted_order" for any order not yet accepted, starts pickup
        for idle riders with orders, and forces idle when no orders remain.
        """
        for order in self.orders:
            if order.id not in self._accepted_ids:
                self._accepted_ids.add(order.id)
                self._record("accepted_order", order.id)
        if self.orders and self.state == IDLE:
            self.state = PICKING_UP
        elif not self.orders and self.state != IDLE:
            self.state = IDLE
            self.special_case = False

    def _complete_order(self, order: Any) -> None:
        """Finish delivery of ``order`` and release it from the rider.

        Args:
            order: The order that has just been delivered.
        """
        tick = globalvar.get_value("current_tick", 0)
        order.complete(tick)
        self.orders.remove(order)
        self._accepted_ids.discard(order.id)
        self._record("delivered_to_customer", order.id)
        self.special_case = False
        self.state = PICKING_UP if self.orders else IDLE

    # ------------------------------------------------------------------
    # Movement
    # ------------------------------------------------------------------
    def move(self) -> None:
        """Advance the rider by one tick.

        Moves towards the current target, handles arrival at the restaurant
        (state 1 -> 2) and at the customer (order completion).
        """
        self._sync_orders()
        if not self.orders:
            return

        order = self.orders[0]
        target = self.current_target()
        if target is None:
            return

        if self.position != target:
            self.special_case = self.x == target[0]
            waypoints = self.planner.plan(self.position, target)
            self.x, self.y, used = self.planner.advance(
                self.x, self.y, waypoints, self.speed)
            self.distance_travelled += used

        if self.position == target:
            self.special_case = False
            if self.state == PICKING_UP:
                self.state = DELIVERING
                self._record("arrived_at_merchant", order.id)
            elif self.state == DELIVERING:
                self._complete_order(order)

    # ------------------------------------------------------------------
    # Logging and serialisation
    # ------------------------------------------------------------------
    def _record(self, event: str, order_id: Optional[int]) -> None:
        """Append a status record to the rider log.

        Args:
            event: Event name such as "spawn" or "delivered_to_customer".
            order_id: Related order id, or None.
        """
        self.log.append({
            "tick": globalvar.get_value("current_tick", 0),
            "rider_id": self.rider_id,
            "event": event,
            "order_id": order_id,
            "state": self.state,
            "x": self.x,
            "y": self.y,
        })

    def to_dict(self) -> Dict[str, Any]:
        """Return a JSON-serialisable snapshot of the rider.

        Returns:
            Dictionary describing the rider and its order ids.
        """
        return {
            "rider_id": self.rider_id,
            "x": self.x,
            "y": self.y,
            "speed": self.speed,
            "state": self.state,
            "special_case": self.special_case,
            "orders": [order.id for order in self.orders],
            "distance_travelled": self.distance_travelled,
        }

    def __repr__(self) -> str:
        return (f"Rider(id={self.rider_id}, pos=({self.x}, {self.y}), "
                f"state={self.state_name}, orders={len(self.orders)})")
