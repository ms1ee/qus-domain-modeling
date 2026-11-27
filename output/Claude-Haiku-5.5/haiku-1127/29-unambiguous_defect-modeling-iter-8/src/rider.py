"""Rider model: movement, state transitions and service logging."""

import random
from typing import Any, Dict, List, Optional, Tuple

import globalvar
from grid_map import LATTICE_STEP, manhattan
from path_planner import PathPlanner

Point = Tuple[int, int]

STATE_IDLE = 0
STATE_PICKING_UP = 1
STATE_DELIVERING = 2
STATE_NAMES = {
    STATE_IDLE: "idle",
    STATE_PICKING_UP: "picking up",
    STATE_DELIVERING: "delivering",
}

MAX_WAIT_TICKS = 2
_PLANNER = PathPlanner()


def _current_tick() -> int:
    """Return the current simulation tick from the global store."""
    return globalvar.get_value("current_tick") or 0


class Rider:
    """A delivery rider that moves along streets and serves orders.

    Attributes:
        rider_id: Unique identifier of the rider.
        x: Current x coordinate.
        y: Current y coordinate.
        speed: Movement speed in units per tick.
        state: 0 idle, 1 picking up, 2 delivering.
        orders: Active orders assigned to this rider.
        special_case: True while on a location point or aligned with target.
        log: Event records with keys "event", "order_id", "tick", "x", "y".
        route: Remaining lattice points toward the current destination.
        distance_traveled: Total distance moved in map units.
    """

    def __init__(self, rider_id: int) -> None:
        """Create a rider on a random road point.

        Args:
            rider_id: Unique identifier assigned by the system.
        """
        self.rider_id = rider_id
        self.x, self.y = _PLANNER.random_road_point()
        base_speed = globalvar.get_value("default_rider_speed") or 50
        self.speed = int(base_speed) * random.choice((1, 2))
        self.state = STATE_IDLE
        self.orders: List[Any] = []
        self.special_case = False
        self.log: List[Dict[str, Any]] = []
        self.route: List[Point] = []
        self.distance_traveled = 0
        self._target: Optional[Point] = None
        self._target_kind: Optional[str] = None
        self._target_order: Any = None
        self._wait_ticks = 0
        self._record("spawn", None)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------
    def has_route(self) -> bool:
        """Return True if the rider still has lattice points to travel.

        Returns:
            True when the remaining route is non-empty.
        """
        return bool(self.route)

    def move(self) -> None:
        """Advance the rider by one tick.

        Accepts newly assigned orders, chooses the next stop, moves along
        the route, and handles arrival events and state transitions.
        """
        self._accept_new_orders()
        if not self.orders:
            self._clear_target()
            self.refresh_state()
            return
        if self._target is None:
            self._choose_next_stop()
        if self._target is not None:
            self._advance()
            if not self.route and (self.x, self.y) == self._target:
                self._arrive()
        self.refresh_state()

    def refresh_state(self) -> None:
        """Recompute the rider state from its orders and current target."""
        if not self.orders:
            self.state = STATE_IDLE
        elif self._target_kind == "dropoff":
            self.state = STATE_DELIVERING
        elif self._target_kind == "pickup":
            self.state = STATE_PICKING_UP
        elif any(o.status == "delivering" for o in self.orders):
            self.state = STATE_DELIVERING
        else:
            self.state = STATE_PICKING_UP

    def reset_route(self) -> None:
        """Clear the current destination so it is re-planned next tick.

        Used by the system to recover from unexpected failures.
        """
        self._clear_target()
        self.refresh_state()

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------
    def _record(self, event: str, order_id: Optional[int]) -> None:
        """Append an event entry to the rider log.

        Args:
            event: Event name, e.g. "accepted_order".
            order_id: Related order identifier or None.
        """
        self.log.append({
            "event": event,
            "order_id": order_id,
            "tick": _current_tick(),
            "rider_id": self.rider_id,
            "x": self.x,
            "y": self.y,
        })

    def _accept_new_orders(self) -> None:
        """Accept orders that were appended to the rider but not yet started."""
        for order in self.orders:
            if order.status in ("created", "assigned"):
                order.assign_to(self.rider_id)
                order.status = "picking_up"
                self._record("accepted_order", order.id)

    def _clear_target(self) -> None:
        """Forget the current destination and remaining route."""
        self._target = None
        self._target_kind = None
        self._target_order = None
        self.route = []

    def _choose_next_stop(self) -> None:
        """Pick the nearest pending stop among all active orders.

        Pickups are available for orders not yet collected; drop-offs are
        available only after the restaurant has been visited. Choosing the
        nearest stop implements the multi-destination optimisation.
        """
        here = (self.x, self.y)
        candidates = []
        for order in self.orders:
            if order.status in ("created", "assigned", "picking_up"):
                candidates.append(("pickup", order.res_pos, order))
            elif order.status == "delivering":
                candidates.append(("dropoff", order.cus_pos, order))
        if not candidates:
            return
        kind, target, order = min(
            candidates, key=lambda c: (manhattan(here, c[1]), c[2].id)
        )
        path = _PLANNER.find_path(here, target)
        if not path:
            # Fallback when no street path exists: keep progressing directly.
            path = [here, target]
        self._target_kind = kind
        self._target = target
        self._target_order = order
        self.route = path[1:]
        self.special_case = (
            _PLANNER.grid.is_location(self.x, self.y)
            or _PLANNER.straight_line_ok(here, target)
        )

    def _blocked(self, point: Point) -> bool:
        """Return True if a stationary rider occupies the given point.

        Args:
            point: Lattice point the rider wants to enter next.

        Returns:
            True if another rider without a route sits on that point.
        """
        for other in globalvar.get_value("riders") or []:
            if other is self:
                continue
            if (other.x, other.y) == point and not other.has_route():
                return True
        return False

    def _advance(self) -> None:
        """Move along the route by up to speed // LATTICE_STEP steps.

        A rider waits up to MAX_WAIT_TICKS when the next point is occupied
        by a stationary rider; after that it proceeds to avoid deadlock.
        """
        budget = max(1, self.speed // LATTICE_STEP)
        while budget > 0 and self.route:
            nxt = self.route[0]
            if self._blocked(nxt):
                self._wait_ticks += 1
                if self._wait_ticks <= MAX_WAIT_TICKS:
                    break
            self.route.pop(0)
            self._wait_ticks = 0
            self.x, self.y = nxt
            self.distance_traveled += LATTICE_STEP
            budget -= 1
        self.special_case = (
            _PLANNER.grid.is_location(self.x, self.y)
            or (self._target is not None
                and _PLANNER.straight_line_ok((self.x, self.y), self._target))
        )

    def _arrive(self) -> None:
        """Handle arrival at the current target.

        At a restaurant the order moves to the delivering stage. At the
        customer the order is completed, removed from the rider, and the fee
        is credited to the system funds.
        """
        order = self._target_order
        if order is None:
            self._clear_target()
            return
        if self._target_kind == "pickup":
            order.status = "delivering"
            self._record("arrived_at_merchant", order.id)
        else:
            order.complete()
            if order in self.orders:
                self.orders.remove(order)
            fee = globalvar.get_value("delivery_fee") or 0
            globalvar.set_value("funds", (globalvar.get_value("funds") or 0) + fee)
            self._record("delivered_to_customer", order.id)
        self._clear_target()
