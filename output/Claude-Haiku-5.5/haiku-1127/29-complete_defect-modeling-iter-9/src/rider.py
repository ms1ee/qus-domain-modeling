"""Rider model: state machine, movement along planned routes and event log."""

import logging

import globalvar
from config import DEFAULT_RIDER_SPEED, HUB_POSITION
from path_planner import PathPlanner

LOGGER = logging.getLogger("dispatch.rider")

STATE_IDLE = 0
STATE_PICKING_UP = 1
STATE_DELIVERING = 2
STATE_NAMES = {
    STATE_IDLE: "idle",
    STATE_PICKING_UP: "picking up",
    STATE_DELIVERING: "delivering",
}


class Rider:
    """A delivery rider that moves on the grid and serves orders.

    Attributes:
        rider_id: Unique identifier.
        x: Current X coordinate (0-800).
        y: Current Y coordinate (0-800).
        speed: Movement speed in units per tick.
        state: 0 = idle, 1 = picking up, 2 = delivering.
        orders: Assigned orders; ``orders[0]`` is the active order.
        special_case: True when the current leg is directly above/below target.
        route: Remaining waypoints of the current leg sequence.
        log: List of event dicts with keys event, order_id, tick, x, y.
    """

    _planner = PathPlanner()

    def __init__(self, rider_id, speed=DEFAULT_RIDER_SPEED, position=HUB_POSITION):
        """Create a rider in the idle state and log its spawn event.

        Args:
            rider_id: Unique integer identifier.
            speed: Movement speed in units per tick (positive integer).
            position: Initial ``(x, y)`` position.

        Raises:
            ValueError: If speed is not a positive integer.
        """
        if isinstance(speed, bool) or not isinstance(speed, int) or speed <= 0:
            raise ValueError(f"rider speed must be a positive integer, got {speed!r}")
        self.rider_id = int(rider_id)
        self.speed = speed
        self.x = int(position[0])
        self.y = int(position[1])
        self.state = STATE_IDLE
        self.orders = []
        self.special_case = False
        self.route = []
        self.log = []
        self._record("spawn", None)

    @property
    def position(self) -> tuple:
        """Current ``(x, y)`` position.

        Returns:
            tuple: Coordinates of the rider.
        """
        return (self.x, self.y)

    @property
    def state_name(self) -> str:
        """Human readable state name.

        Returns:
            str: "idle", "picking up" or "delivering".
        """
        return STATE_NAMES.get(self.state, "unknown")

    def reset(self) -> None:
        """Return the rider to a clean idle state without touching orders."""
        self.state = STATE_IDLE
        self.route = []
        self.special_case = False

    def move(self) -> None:
        """Advance the rider by one tick.

        Handles the idle→picking up transition when an order is assigned,
        movement along the route, the picking up→delivering transition on
        arrival at the restaurant, and the delivering→idle transition on
        delivery to the customer. Each transition appends a log entry.
        """
        if self.state == STATE_IDLE:
            if not self.orders:
                self.special_case = False
                return
            self.state = STATE_PICKING_UP
            order = self.orders[0]
            order.mark_picking_up()
            self._set_route(order.restaurant)
            self._record("accepted_order", order.id)

        if not self.orders:
            LOGGER.warning("Rider %s was busy without orders; resetting", self.rider_id)
            self.reset()
            return

        order = self.orders[0]
        order.distance += self._advance(self.speed)
        if self.route:
            return

        if self.state == STATE_PICKING_UP:
            self.state = STATE_DELIVERING
            order.mark_delivering()
            self._record("arrived_at_merchant", order.id)
            self._set_route(order.customer)

        if self.state == STATE_DELIVERING and not self.route:
            self._complete_current_order()

    def _complete_current_order(self) -> None:
        """Finish the active order, log delivery and return to idle."""
        order = self.orders.pop(0)
        order.mark_completed(self._tick())
        self._record("delivered_to_customer", order.id)
        self.reset()

    def _set_route(self, target) -> None:
        """Plan the waypoints from the current position to ``target``.

        Args:
            target: ``(x, y)`` destination.
        """
        self.route = self._planner.plan(self.position, target)
        self.special_case = self.x == int(target[0]) and self.y != int(target[1])

    def _advance(self, budget: int) -> int:
        """Spend up to ``budget`` units moving along the planned route.

        Args:
            budget: Maximum number of units to move this tick.

        Returns:
            int: Number of units actually moved.
        """
        moved_total = 0
        while budget > 0 and self.route:
            tx, ty = self.route[0]
            dx = tx - self.x
            dy = ty - self.y
            distance = abs(dx) + abs(dy)
            if distance <= budget:
                self.x, self.y = tx, ty
                budget -= distance
                moved_total += distance
                self.route.pop(0)
            else:
                step_x = min(budget, abs(dx))
                step_y = min(budget - step_x, abs(dy))
                self.x += step_x if dx > 0 else -step_x
                self.y += step_y if dy > 0 else -step_y
                moved_total += step_x + step_y
                budget = 0
        return moved_total

    def _tick(self) -> int:
        """Return the current simulation tick from the global store.

        Returns:
            int: Current tick (0 if unset).
        """
        return int(globalvar.get_value("current_tick", 0) or 0)

    def _record(self, event: str, order_id) -> None:
        """Append an entry to the rider's event log.

        Args:
            event: Event name (spawn, accepted_order, arrived_at_merchant,
                delivered_to_customer).
            order_id: Related order identifier, or None.
        """
        self.log.append({
            "event": event,
            "order_id": order_id,
            "tick": self._tick(),
            "x": self.x,
            "y": self.y,
        })

    def to_dict(self) -> dict:
        """Serialise the rider to a JSON-compatible dictionary.

        Returns:
            dict: Rider fields, with orders represented by identifiers.
        """
        return {
            "rider_id": self.rider_id,
            "x": self.x,
            "y": self.y,
            "speed": self.speed,
            "state": self.state,
            "orders": [order.id for order in self.orders],
            "special_case": self.special_case,
            "log": list(self.log),
        }
