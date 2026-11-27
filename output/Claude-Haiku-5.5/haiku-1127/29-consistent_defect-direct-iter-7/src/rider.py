"""Rider model: state machine, movement along streets and event log.

Rider states:
    0 (IDLE): no active orders.
    1 (PICKING_UP): travelling to the restaurant of the current order.
    2 (DELIVERING): travelling to the customer of the current order.

Orders are served first-in first-out. An order is assigned by appending it
to ``rider.orders``; the state transitions and log entries happen in
``move()``.
"""

import logging
from typing import Any, Dict, List, Mapping, Optional, Tuple

import globalvar
from path_planner import PathPlanner

logger = logging.getLogger(__name__)

IDLE = 0
PICKING_UP = 1
DELIVERING = 2

STATE_NAMES = {IDLE: "idle", PICKING_UP: "picking up", DELIVERING: "delivering"}

SPAWN_X = 400
SPAWN_Y = 400
DEFAULT_SPEED = 20  # units per tick


def _current_tick() -> int:
    """Return the simulated time stored in the global variables."""
    return int(globalvar.get_value("tick", 0) or 0)


class Rider:
    """A delivery rider that moves along the street grid.

    Attributes:
        rider_id: Unique identifier.
        x, y: Current position (integers, 0-800).
        speed: Movement speed in units per tick.
        state: Rider status enum (0 idle, 1 picking up, 2 delivering).
        orders: All orders assigned to this rider, including completed ones
            kept as delivery history.
        special_case: True while the current leg is a straight-line move
            (target directly above, below, left or right).
        target: Current destination (x, y) or None.
        route: Remaining waypoints for the current leg.
        log: Chronological list of event dictionaries with keys
            "event", "order_id", "tick", "x", "y" and "state".
    """

    def __init__(
        self,
        rider_id: int,
        x: int = SPAWN_X,
        y: int = SPAWN_Y,
        speed: int = DEFAULT_SPEED,
    ) -> None:
        """Create a rider and log its spawn event.

        Args:
            rider_id: Unique rider identifier.
            x: Starting x coordinate (default 400).
            y: Starting y coordinate (default 400).
            speed: Movement speed in units per tick.
        """
        self.rider_id = int(rider_id)
        self.x = int(x)
        self.y = int(y)
        self.speed = int(speed)
        self.state = IDLE
        self.orders: List[Any] = []
        self.special_case = False
        self.target: Optional[Tuple[int, int]] = None
        self.route: List[Tuple[int, int]] = []
        self.log: List[Dict[str, Any]] = []
        self.log_event("spawn", None)

    @property
    def position(self) -> Tuple[int, int]:
        """Return the current (x, y) position."""
        return (self.x, self.y)

    @property
    def state_name(self) -> str:
        """Return a human-readable name for the current state."""
        return STATE_NAMES.get(self.state, "unknown")

    def active_orders(self) -> List[Any]:
        """Return orders that are not yet completed, in FIFO order."""
        return [order for order in self.orders if order.status != "completed"]

    def current_order(self) -> Optional[Any]:
        """Return the order currently being served, or None."""
        active = self.active_orders()
        return active[0] if active else None

    def log_event(self, event: str, order_id: Optional[int]) -> Dict[str, Any]:
        """Append an event entry to the rider log.

        Args:
            event: One of spawn, accepted_order, arrived_at_merchant,
                delivered_to_customer.
            order_id: Related order ID, or None for spawn events.

        Returns:
            The log entry that was appended.
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
        logger.info(
            "rider=%s tick=%s event=%s order=%s pos=(%s,%s)",
            self.rider_id,
            entry["tick"],
            event,
            order_id,
            self.x,
            self.y,
        )
        return entry

    def _set_target(self, target: Tuple[int, int]) -> None:
        """Set the destination for the current leg and plan its route.

        Args:
            target: Destination (x, y).
        """
        self.target = (int(target[0]), int(target[1]))
        self.route = PathPlanner.plan(self.position, self.target)
        self.special_case = PathPlanner.is_special_case(self.position, self.target)

    def _travel(self, budget: int) -> int:
        """Move along the planned route using up to ``budget`` units.

        Args:
            budget: Maximum distance to travel this tick.

        Returns:
            Unused budget (0 if the rider used it all).
        """
        remaining = budget
        while remaining > 0 and self.route:
            wx, wy = self.route[0]
            dx = wx - self.x
            dy = wy - self.y
            dist = abs(dx) + abs(dy)
            if dist == 0:
                self.route.pop(0)
                continue
            if dx != 0 and dy != 0:
                # Routes are axis-aligned; this branch is a safety net.
                logger.warning("rider=%s non-axis segment; snapping", self.rider_id)
                self.x, self.y = wx, wy
                self.route.pop(0)
                continue
            if dist <= remaining:
                self.x, self.y = wx, wy
                remaining -= dist
                self.route.pop(0)
            else:
                if dx != 0:
                    self.x += remaining if dx > 0 else -remaining
                else:
                    self.y += remaining if dy > 0 else -remaining
                remaining = 0
        return remaining

    def move(self) -> None:
        """Advance the rider by one tick.

        Handles the state transitions:
            IDLE -> PICKING_UP when an order is accepted.
            PICKING_UP -> DELIVERING on arrival at the restaurant.
            DELIVERING -> PICKING_UP (next order) or IDLE on delivery.
        """
        order = self.current_order()
        if order is None:
            if self.state != IDLE or self.route or self.target is not None:
                self.state = IDLE
                self.target = None
                self.route = []
                self.special_case = False
            return

        if self.state == IDLE:
            self.state = PICKING_UP
            order.mark_picking_up()
            self.log_event("accepted_order", order.id)
            self._set_target(order.res_pos)
        elif self.target is None:
            destination = order.res_pos if self.state == PICKING_UP else order.cus_pos
            self._set_target(destination)

        self._travel(self.speed)
        if self.route:
            return

        if self.state == PICKING_UP:
            self._arrive_at_merchant(order)
        elif self.state == DELIVERING:
            self._deliver(order)

    def _arrive_at_merchant(self, order: Any) -> None:
        """Handle arrival at the restaurant and head for the customer.

        Args:
            order: Order being picked up.
        """
        order.mark_picked_up(_current_tick())
        self.state = DELIVERING
        self.log_event("arrived_at_merchant", order.id)
        self._set_target(order.cus_pos)

    def _deliver(self, order: Any) -> None:
        """Handle delivery to the customer and move to the next order.

        Args:
            order: Order that has just been delivered.
        """
        order.mark_completed(_current_tick())
        self.log_event("delivered_to_customer", order.id)
        self.target = None
        self.route = []
        self.special_case = False
        next_order = self.current_order()
        if next_order is None:
            self.state = IDLE
            return
        self.state = PICKING_UP
        next_order.mark_picking_up()
        self.log_event("accepted_order", next_order.id)
        self._set_target(next_order.res_pos)

    def to_dict(self) -> Dict[str, Any]:
        """Serialise the rider to a JSON-compatible dictionary."""
        return {
            "rider_id": self.rider_id,
            "x": self.x,
            "y": self.y,
            "speed": self.speed,
            "state": self.state,
            "special_case": self.special_case,
            "target": list(self.target) if self.target else None,
            "route": [list(point) for point in self.route],
            "order_ids": [order.id for order in self.orders],
            "log": self.log,
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, Any], orders_by_id: Mapping[int, Any]) -> "Rider":
        """Rebuild a rider from ``to_dict`` output.

        Args:
            data: Dictionary produced by ``to_dict``.
            orders_by_id: Lookup of Order objects keyed by order ID.

        Returns:
            Restored Rider instance.
        """
        rider = cls(
            data["rider_id"],
            data.get("x", SPAWN_X),
            data.get("y", SPAWN_Y),
            data.get("speed", DEFAULT_SPEED),
        )
        rider.state = int(data.get("state", IDLE))
        rider.special_case = bool(data.get("special_case", False))
        target = data.get("target")
        rider.target = (int(target[0]), int(target[1])) if target else None
        rider.route = [(int(p[0]), int(p[1])) for p in data.get("route", [])]
        rider.orders = [
            orders_by_id[oid] for oid in data.get("order_ids", []) if oid in orders_by_id
        ]
        rider.log = list(data.get("log", []))
        return rider
