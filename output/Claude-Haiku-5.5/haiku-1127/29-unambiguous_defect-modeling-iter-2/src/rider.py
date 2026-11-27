"""Rider model: state machine, movement, and event logging.

Rider states:
    0 = idle, 1 = picking up (heading to the restaurant),
    2 = delivering (heading to the customer).

Events written to ``Rider.log``:
    spawn, accepted_order, arrived_at_merchant, delivered_to_customer,
    recovered.
"""

import logging
import random
from typing import Any, Dict, List, Optional, Tuple

from globalvar import get_value, set_value
from grid_map import CELL_SIZE, GRID_DIMENSION, MAP_SIZE, is_on_street
from path_planner import PathPlanner

logger = logging.getLogger(__name__)

_DEFAULT_PLANNER = PathPlanner()


def _sign(value: int) -> int:
    """Return -1, 0 or 1 according to the sign of ``value``."""
    return (value > 0) - (value < 0)


class Rider:
    """A delivery rider moving on the street grid.

    Attributes:
        rider_id (int): Unique identifier.
        x (int): Current X coordinate.
        y (int): Current Y coordinate.
        speed (int): Distance units travelled per tick.
        state (int): 0 idle, 1 picking up, 2 delivering.
        orders (list[Order]): Assigned orders; index 0 is the active one.
        special_case (bool): True while the rider is inside a location cell
            (off the streets).
        path (list[tuple[int, int]]): Remaining waypoints of the current leg.
        target (tuple[int, int] | None): Current destination.
        log (list[dict]): Chronological status-change records.
    """

    IDLE = 0
    PICKING_UP = 1
    DELIVERING = 2
    STATE_NAMES = {IDLE: "idle", PICKING_UP: "picking up",
                   DELIVERING: "delivering"}
    MIN_SPEED = 20
    MAX_SPEED = 40

    def __init__(self, rider_id: int, x: Optional[int] = None,
                 y: Optional[int] = None, speed: Optional[int] = None,
                 planner: Optional[PathPlanner] = None):
        """Create a rider, spawning it on a street if no position is given.

        Args:
            rider_id (int): Unique rider identifier.
            x (int | None): Optional starting X coordinate (must be on road).
            y (int | None): Optional starting Y coordinate.
            speed (int | None): Optional speed; random in 20-40 otherwise.
            planner (PathPlanner | None): Planner to use for routing.

        Raises:
            ValueError: If the speed is not positive.
        """
        self.rider_id = int(rider_id)
        if x is None or y is None:
            x, y = self._random_road_point()
        self.x = int(x)
        self.y = int(y)
        self.speed = (int(speed) if speed is not None
                      else random.randint(self.MIN_SPEED, self.MAX_SPEED))
        if self.speed <= 0:
            raise ValueError("Rider speed must be positive.")
        self.state = self.IDLE
        self.orders: List[Any] = []
        self.special_case = False
        self.path: List[Tuple[int, int]] = []
        self.target: Optional[Tuple[int, int]] = None
        self.planner = planner or _DEFAULT_PLANNER
        self.log: List[Dict[str, Any]] = []
        self._record("spawn", None)

    @staticmethod
    def _random_road_point() -> Tuple[int, int]:
        """Pick a random point on a vertical street.

        Returns:
            tuple[int, int]: Road coordinates (x is a multiple of 100).
        """
        x = random.randint(0, GRID_DIMENSION) * CELL_SIZE
        y = random.randint(0, MAP_SIZE)
        return x, y

    @property
    def position(self) -> Tuple[int, int]:
        """tuple[int, int]: Current (x, y) position."""
        return self.x, self.y

    @staticmethod
    def _current_tick() -> int:
        """Return the simulated tick from the global store."""
        return int(get_value("current_tick", 0) or 0)

    def _record(self, event: str, order_id: Optional[int]) -> None:
        """Append a status-change entry to the rider log.

        Args:
            event (str): Event name.
            order_id (int | None): Related order id, if any.
        """
        entry = {
            "event": event,
            "order_id": order_id,
            "tick": self._current_tick(),
            "rider_id": self.rider_id,
            "x": self.x,
            "y": self.y,
            "state": self.state,
        }
        self.log.append(entry)
        logger.debug("Rider %s %s order=%s at (%s,%s)", self.rider_id,
                     event, order_id, self.x, self.y)

    def _update_special_case(self) -> None:
        """Set ``special_case`` when the rider is off the streets."""
        self.special_case = not is_on_street(self.x, self.y)

    def accept_order(self, order) -> None:
        """Accept an order by appending it to ``orders``.

        If the rider is idle it immediately starts the pickup leg.

        Args:
            order (Order): Order to accept.
        """
        self.orders.append(order)
        self._record("accepted_order", order.id)
        if self.state == self.IDLE:
            self._begin_pickup()

    def _begin_pickup(self) -> None:
        """Start the leg from the current position to the active restaurant."""
        order = self.orders[0]
        self.state = self.PICKING_UP
        order.mark_picking_up()
        self.target = order.res_pos
        self.path = self.planner.plan(self.position, self.target)
        self._update_special_case()

    def _set_idle(self) -> None:
        """Return the rider to the idle state and clear the route."""
        self.state = self.IDLE
        self.target = None
        self.path = []
        self._update_special_case()

    def _sync_path_state(self) -> None:
        """Keep the path and target consistent with the rider state."""
        if self.state == self.IDLE:
            self.target = None
            self.path = []

    def _advance(self) -> int:
        """Move along the current path by up to ``speed`` units.

        Moves are axis-aligned: the rider first covers the horizontal part of
        a waypoint, then the vertical part.

        Returns:
            int: Number of distance units actually travelled.
        """
        remaining = self.speed
        moved = 0
        while remaining > 0 and self.path:
            tx, ty = self.path[0]
            dx = tx - self.x
            dy = ty - self.y
            dist = abs(dx) + abs(dy)
            if dist == 0:
                self.path.pop(0)
                continue
            step = min(dist, remaining)
            step_x = min(abs(dx), step)
            step_y = step - step_x
            self.x += _sign(dx) * step_x
            self.y += _sign(dy) * step_y
            remaining -= step
            moved += step
            if (self.x, self.y) == (tx, ty):
                self.path.pop(0)
        return moved

    def _handle_arrival(self) -> None:
        """Process arrival at the current target and advance the state machine.

        Pickup arrival: state 1 -> 2, plan route to the customer.
        Delivery arrival: order completed, state 2 -> 0 or next pickup.
        """
        order = self.orders[0]
        if self.state == self.PICKING_UP:
            self.state = self.DELIVERING
            order.mark_delivering()
            self._record("arrived_at_merchant", order.id)
            self.target = order.cus_pos
            self.path = self.planner.plan(self.position, self.target)
        elif self.state == self.DELIVERING:
            order.mark_completed(self._current_tick())
            self.orders.pop(0)
            self._record("delivered_to_customer", order.id)
            history = get_value("order_history")
            if history is not None:
                history.append(order)
            if self.orders:
                self._begin_pickup()
            else:
                self._set_idle()
        else:
            self._set_idle()
        self._update_special_case()

    def move(self) -> None:
        """Advance the rider by one tick.

        Performs the idle -> picking up -> delivering -> idle transitions,
        moves along the planned route, and accumulates travelled distance on
        the active order.
        """
        if not self.orders:
            if self.state != self.IDLE:
                self._set_idle()
            return

        if self.state == self.IDLE:
            # Orders appended directly to ``orders`` are accepted here.
            self._record("accepted_order", self.orders[0].id)
            self._begin_pickup()

        moved = self._advance()
        if moved and self.orders:
            self.orders[0].add_distance(moved)

        while self.orders and not self.path and self.target is not None:
            self._handle_arrival()
        self._sync_path_state()
        self._update_special_case()

    def recover(self) -> None:
        """Restore a consistent state after an unexpected error.

        The route is re-planned for the active order, or the rider is set
        idle if it has no orders.
        """
        self.path = []
        self.target = None
        if self.orders:
            self._begin_pickup()
            self._record("recovered", self.orders[0].id)
        else:
            self._set_idle()
            self._record("recovered", None)
        logger.warning("Rider %s recovered to a consistent state.",
                       self.rider_id)

    def to_dict(self) -> Dict[str, Any]:
        """Serialise the rider for JSON persistence.

        Returns:
            dict: JSON-compatible representation.
        """
        return {
            "rider_id": self.rider_id,
            "x": self.x,
            "y": self.y,
            "speed": self.speed,
            "state": self.state,
            "special_case": self.special_case,
            "order_ids": [o.id for o in self.orders],
        }

    def __repr__(self) -> str:
        """Return a concise representation for debugging."""
        return (f"Rider(id={self.rider_id}, pos=({self.x},{self.y}), "
                f"state={self.state}, orders={len(self.orders)})")
