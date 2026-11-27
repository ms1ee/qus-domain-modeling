"""Rider model: state machine, street-constrained movement and event log."""

import logging
import random
from typing import Any, Dict, List, Optional, Tuple

import globalvar
from config import (
    STATE_DELIVERING,
    STATE_IDLE,
    STATE_NAMES,
    STATE_PICKING_UP,
    param,
)
from path_planner import PathPlanner, random_road_point

logger = logging.getLogger("dispatch.rider")

EVENT_SPAWN = "spawn"
EVENT_ACCEPTED = "accepted_order"
EVENT_ARRIVED_MERCHANT = "arrived_at_merchant"
EVENT_DELIVERED = "delivered_to_customer"

Point = Tuple[int, int]


def _current_tick() -> int:
    """Return the simulated time stored in the global variable store."""
    return globalvar.get_value("tick", 0)


def occupancy_map(exclude: Optional["Rider"] = None) -> Dict[Point, int]:
    """Count riders at each map point, optionally excluding one rider.

    Args:
        exclude: Rider to ignore (typically the rider being planned).

    Returns:
        Mapping of ``(x, y)`` to the number of riders located there.
    """
    counts: Dict[Point, int] = {}
    for rider in globalvar.get_value("riders", []) or []:
        if rider is exclude:
            continue
        key = (rider.x, rider.y)
        counts[key] = counts.get(key, 0) + 1
    return counts


class Rider:
    """A delivery rider that moves along streets and serves orders.

    Attributes:
        rider_id: Unique identifier.
        x, y: Current integer coordinates on the street network.
        speed: Movement budget per tick, in map units.
        state: 0 = idle, 1 = picking up, 2 = delivering.
        orders: Assigned orders; the first element is the active order.
        special_case: True when the current target lies directly above,
            below, or beside the rider on the same street.
        path: Remaining waypoints for the current leg.
        log: Chronological list of event dictionaries. Each entry contains
            at least ``event`` and ``order_id``.
    """

    def __init__(self, rider_id: int) -> None:
        """Create a rider at a random street position in idle state.

        Args:
            rider_id: Unique identifier assigned by the system manager.
        """
        self.rider_id = rider_id
        self.x, self.y = random_road_point()
        self.speed = random.randint(param("speed_min"), param("speed_max"))
        self.state = STATE_IDLE
        self.orders: List[Any] = []
        self.special_case = False
        self.path: List[Point] = []
        self.log: List[Dict[str, Any]] = []
        self._planner = PathPlanner()
        self._record(EVENT_SPAWN, None)
        logger.info("Rider %s spawned at (%s, %s) speed %s",
                    rider_id, self.x, self.y, self.speed)

    # ------------------------------------------------------------------
    # Properties
    # ------------------------------------------------------------------
    @property
    def position(self) -> Point:
        """Current ``(x, y)`` position."""
        return self.x, self.y

    @property
    def state_name(self) -> str:
        """Human-readable state label."""
        return STATE_NAMES.get(self.state, "unknown")

    @property
    def current_order(self):
        """The order currently being served, or None."""
        return self.orders[0] if self.orders else None

    # ------------------------------------------------------------------
    # Logging
    # ------------------------------------------------------------------
    def _record(self, event: str, order_id: Optional[int]) -> None:
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
        logger.info("t=%s rider=%s event=%s order=%s pos=(%s,%s)",
                    entry["tick"], self.rider_id, event, order_id, self.x, self.y)

    # ------------------------------------------------------------------
    # Public behaviour
    # ------------------------------------------------------------------
    def move(self) -> None:
        """Advance the rider by one tick.

        Handles state transitions:
          * Idle -> Picking up when an assigned order exists (``accepted_order``).
          * Picking up -> Delivering on reaching the restaurant
            (``arrived_at_merchant``).
          * Delivering -> Idle on reaching the customer
            (``delivered_to_customer``).
        """
        if self.state == STATE_IDLE:
            if not self.orders:
                return
            self._start_pickup(self.orders[0])
        elif not self.orders:
            logger.warning("Rider %s was active without orders; resetting",
                           self.rider_id)
            self._reset_idle()
            return

        if self.path:
            self._advance()
        if not self.path:
            self._handle_arrival()

    def remaining_distance(self) -> int:
        """Estimate the distance still to travel for all assigned orders.

        Returns:
            Total Manhattan distance in map units.
        """
        if not self.orders:
            return 0
        total = 0
        current = self.position
        first = self.orders[0]
        if self.state == STATE_PICKING_UP:
            total += self._planner.route_length(current, self.path)
            current = first.res_pos
            stops = [first.cus_pos]
        elif self.state == STATE_DELIVERING:
            total += self._planner.route_length(current, self.path)
            current = first.cus_pos
            stops = []
        else:
            stops = [first.res_pos, first.cus_pos]
        for order in self.orders[1:]:
            stops.extend([order.res_pos, order.cus_pos])
        for stop in stops:
            total += self._planner.manhattan(current, stop)
            current = stop
        return total

    def to_dict(self) -> Dict[str, Any]:
        """Return a JSON-serialisable snapshot of the rider."""
        return {
            "rider_id": self.rider_id,
            "x": self.x,
            "y": self.y,
            "speed": self.speed,
            "state": self.state,
            "special_case": self.special_case,
            "order_ids": [order.id for order in self.orders],
        }

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------
    def _start_pickup(self, order) -> None:
        """Transition from idle to picking up for ``order``."""
        self.state = STATE_PICKING_UP
        order.mark_picking_up(_current_tick())
        self._record(EVENT_ACCEPTED, order.id)
        self._set_path(order.res_pos)

    def _handle_arrival(self) -> None:
        """Process arrival at the current target and transition state."""
        if not self.orders:
            self._reset_idle()
            return
        order = self.orders[0]
        if self.state == STATE_PICKING_UP:
            self.state = STATE_DELIVERING
            order.mark_delivering(_current_tick())
            self._record(EVENT_ARRIVED_MERCHANT, order.id)
            self._set_path(order.cus_pos)
        elif self.state == STATE_DELIVERING:
            order.complete(_current_tick())
            self.orders.pop(0)
            self._reset_idle()
            globalvar.set_value(
                "funds", globalvar.get_value("funds", 0) + param("order_revenue"))
            self._record(EVENT_DELIVERED, order.id)
            logger.info("Order %s completed by rider %s", order.id, self.rider_id)

    def _set_path(self, target: Point) -> None:
        """Plan a route to ``target`` avoiding congested corners."""
        self.path = self._planner.plan(self.position, target, occupancy_map(exclude=self))
        self.special_case = self.x == target[0] or self.y == target[1]

    def _reset_idle(self) -> None:
        """Return the rider to the idle state and clear the route."""
        self.state = STATE_IDLE
        self.path = []
        self.special_case = False

    def _advance(self) -> None:
        """Move along the planned waypoints using up to ``speed`` units."""
        budget = self.speed
        while budget > 0 and self.path:
            tx, ty = self.path[0]
            dx = tx - self.x
            dy = ty - self.y
            if dx == 0 and dy == 0:
                self.path.pop(0)
                continue
            distance = abs(dx) + abs(dy)
            if distance <= budget:
                self.x, self.y = tx, ty
                budget -= distance
                self.path.pop(0)
            else:
                step_x = min(abs(dx), budget)
                self.x += step_x if dx > 0 else -step_x
                budget -= step_x
                step_y = min(abs(dy), budget)
                self.y += step_y if dy > 0 else -step_y
                budget -= step_y
