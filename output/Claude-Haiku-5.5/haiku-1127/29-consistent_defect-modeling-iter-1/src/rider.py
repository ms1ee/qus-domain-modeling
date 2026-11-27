"""Rider model: state machine, movement along streets and delivery log."""

from typing import Any, Dict, List, Optional, Tuple

from globalvar import get_value
from order_model import Order
from path_planner import PathPlanner, Point

STATE_IDLE = 0
STATE_PICKING_UP = 1
STATE_DELIVERING = 2
STATE_NAMES = {STATE_IDLE: "idle", STATE_PICKING_UP: "picking up", STATE_DELIVERING: "delivering"}

DEFAULT_RIDER_SPEED = 20
SPAWN_X = 400
SPAWN_Y = 400
ACTIVE_STATUSES = ("assigned", "picking_up", "delivering")


class Rider:
    """A delivery rider that moves along the street grid.

    Attributes:
        rider_id: Unique identifier.
        x, y: Current coordinates.
        speed: Units moved per tick.
        state: 0 = idle, 1 = picking up, 2 = delivering.
        orders: All orders ever assigned (completed ones kept as history).
        special_case: True while heading directly above/below the target.
        log: Status-change entries (dicts with "event" and "order_id").
    """

    def __init__(
        self,
        rider_id: int,
        x: int = SPAWN_X,
        y: int = SPAWN_Y,
        speed: int = DEFAULT_RIDER_SPEED,
    ) -> None:
        self.rider_id: int = int(rider_id)
        self.x: int = int(x)
        self.y: int = int(y)
        self.speed: int = int(speed)
        self.state: int = STATE_IDLE
        self.orders: List[Order] = []
        self.special_case: bool = False
        self.log: List[Dict[str, Any]] = []
        self._path: List[Point] = []
        self._planner = PathPlanner()
        self._record("spawn", None)

    # ------------------------------------------------------------------ #
    # Queries
    # ------------------------------------------------------------------ #
    @property
    def position(self) -> Point:
        """Current (x, y) position."""
        return self.x, self.y

    def active_orders(self) -> List[Order]:
        """Return orders that are assigned but not yet completed."""
        return [o for o in self.orders if o.status in ACTIVE_STATUSES]

    def is_available(self) -> bool:
        """Return True if the rider has no active orders (idle resource)."""
        return not self.active_orders()

    def current_order(self) -> Optional[Order]:
        """Return the order currently being picked up or delivered."""
        for order in self.orders:
            if order.status in ("picking_up", "delivering"):
                return order
        return None

    def _next_assigned(self) -> Optional[Order]:
        """Return the first queued order that has not been started."""
        for order in self.orders:
            if order.status == "assigned":
                return order
        return None

    def _now(self) -> int:
        """Return the current simulated time."""
        return int(get_value("simulated_time", 0) or 0)

    def _record(self, event: str, order_id: Optional[int]) -> None:
        """Append a status-change entry to the rider log."""
        self.log.append(
            {
                "event": event,
                "order_id": order_id,
                "time": self._now(),
                "rider_id": self.rider_id,
                "x": self.x,
                "y": self.y,
                "state": self.state,
            }
        )

    def _other_positions(self) -> List[Point]:
        """Return positions of all other riders (for conflict avoidance)."""
        riders = get_value("riders") or []
        return [r.position for r in riders if r is not self]

    # ------------------------------------------------------------------ #
    # Route handling
    # ------------------------------------------------------------------ #
    def _set_path(self, target: Point) -> None:
        """Plan a street-first route to ``target`` and update flags."""
        self.special_case = self._planner.is_vertical_alignment(self.position, target)
        self._path = self._planner.plan(self.position, target, occupied=self._other_positions())

    def _target_for(self, order: Order) -> Point:
        """Return the current destination for the rider's order."""
        return order.res_pos if self.state == STATE_PICKING_UP else order.cus_pos

    def _advance(self) -> None:
        """Move up to ``speed`` units along the planned waypoints."""
        remaining = self.speed
        while remaining > 0 and self._path:
            tx, ty = self._path[0]
            dx = tx - self.x
            dy = ty - self.y
            dist = abs(dx) + abs(dy)
            if dist == 0:
                self._path.pop(0)
                continue
            if dist <= remaining:
                self.x, self.y = tx, ty
                self._path.pop(0)
                remaining -= dist
                continue
            # Partial move along the current axis-aligned segment.
            if dx != 0:
                step = min(abs(dx), remaining) * (1 if dx > 0 else -1)
                self.x += step
                remaining -= abs(step)
            if remaining > 0 and dy != 0:
                step = min(abs(dy), remaining) * (1 if dy > 0 else -1)
                self.y += step
                remaining -= abs(step)

    # ------------------------------------------------------------------ #
    # State transitions
    # ------------------------------------------------------------------ #
    def _start_pickup(self, order: Order) -> None:
        """Idle/Delivering -> Picking up: accept a queued order."""
        self.state = STATE_PICKING_UP
        order.set_status("picking_up")
        self._record("accepted_order", order.id)
        self._set_path(order.res_pos)

    def _on_arrival(self, order: Order) -> None:
        """Handle arrival at the current destination."""
        if self.state == STATE_PICKING_UP:
            # Picking Up -> Delivering on arrival at the restaurant.
            self.state = STATE_DELIVERING
            order.set_status("delivering")
            self._record("arrived_at_merchant", order.id)
            self._set_path(order.cus_pos)
        elif self.state == STATE_DELIVERING:
            # Delivering -> Picking up (next order) or Idle.
            order.complete(self._now())
            self._record("delivered_to_customer", order.id)
            nxt = self._next_assigned()
            if nxt is not None:
                self._start_pickup(nxt)
            else:
                self.state = STATE_IDLE
                self._path = []
                self.special_case = False

    def move(self) -> None:
        """Advance the rider by one tick.

        Handles Idle -> Picking up when an order is queued, movement along
        the planned route, and arrival-driven state transitions.
        """
        if self.state == STATE_IDLE:
            nxt = self._next_assigned()
            if nxt is None:
                return
            self._start_pickup(nxt)

        order = self.current_order()
        if order is None:
            self.state = STATE_IDLE
            self._path = []
            return

        target = self._target_for(order)
        if not self._path and self.position != target:
            self._set_path(target)

        self._advance()

        if not self._path and self.position == target:
            self._on_arrival(order)

    def to_dict(self) -> Dict[str, Any]:
        """Return a JSON-serialisable representation of the rider."""
        return {
            "rider_id": self.rider_id,
            "x": self.x,
            "y": self.y,
            "speed": self.speed,
            "state": self.state,
            "special_case": self.special_case,
            "orders": [o.id for o in self.orders],
        }

    def __repr__(self) -> str:
        return f"Rider(id={self.rider_id}, pos=({self.x},{self.y}), state={self.state})"
