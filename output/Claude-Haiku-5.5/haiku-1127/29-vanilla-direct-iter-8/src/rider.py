"""Rider entity: state machine, movement and order execution.

A rider processes the orders in ``rider.orders`` in sequence. For the first
order it drives to the restaurant (state 1, picking up), then to the customer
(state 2, delivering), and finally becomes idle (state 0). Every status change
is recorded in ``rider.log``.
"""

import logging
import math

import globalvar
from config import SETTINGS
from path_planner import PathPlanner

logger = logging.getLogger(__name__)

STATE_IDLE = 0
STATE_PICKING_UP = 1
STATE_DELIVERING = 2

STATE_NAMES = {
    STATE_IDLE: "idle",
    STATE_PICKING_UP: "picking up",
    STATE_DELIVERING: "delivering",
}


def _current_tick():
    """Return the simulated clock value (0 if unset)."""
    return globalvar.get_value("tick") or 0


class Rider:
    """A delivery rider.

    Attributes:
        rider_id (int): Unique identifier.
        x (int): Current x coordinate.
        y (int): Current y coordinate.
        speed (int): Movement distance per tick.
        state (int): 0 idle, 1 picking up, 2 delivering.
        orders (list[Order]): Assigned orders; index 0 is the active order.
        special_case (bool): True while the rider is off the street grid
            (initial position, snapping to a street, or the final approach to
            a cell-centre location).
        target (tuple or None): Current destination.
        route (list[tuple]): Remaining waypoints to the destination.
        log (list[dict]): Status change records with keys ``event``,
            ``order_id``, ``tick``, ``x``, ``y`` and ``state``.
    """

    def __init__(self, rider_id):
        """Create a rider at the configured start location.

        Args:
            rider_id: Unique integer identifier of the rider.
        """
        self.rider_id = int(rider_id)
        self.x = SETTINGS["rider_start_x"]
        self.y = SETTINGS["rider_start_y"]
        self.speed = SETTINGS["rider_speed"]
        self.state = STATE_IDLE
        self.orders = []
        self.special_case = not PathPlanner.is_street(self.x, self.y)
        self.target = None
        self.route = []
        self.log = []
        self._record("spawn", None)

    # ------------------------------------------------------------------ #
    # Accessors
    # ------------------------------------------------------------------ #
    @property
    def state_name(self):
        """str: Human-readable name of the current state."""
        return STATE_NAMES.get(self.state, "unknown")

    def position(self):
        """Return the current position.

        Returns:
            tuple: ``(x, y)``.
        """
        return (self.x, self.y)

    def distance_to(self, point):
        """Return the Euclidean distance from the rider to ``point``.

        Args:
            point: ``(x, y)`` target.

        Returns:
            float: The straight-line distance.
        """
        return math.hypot(self.x - point[0], self.y - point[1])

    # ------------------------------------------------------------------ #
    # Logging
    # ------------------------------------------------------------------ #
    def _record(self, event, order_id):
        """Append a status change record to ``self.log``.

        Args:
            event: One of "spawn", "accepted_order", "arrived_at_merchant",
                "delivered_to_customer".
            order_id: Related order ID, or None.
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
        logger.debug("Rider #%d %s (order %s)", self.rider_id, event, order_id)

    # ------------------------------------------------------------------ #
    # State transitions
    # ------------------------------------------------------------------ #
    def _set_target(self, target):
        """Set the destination and plan the route to it.

        Args:
            target: ``(x, y)`` destination.
        """
        self.target = (int(target[0]), int(target[1]))
        self.route = PathPlanner.plan_route(self.position(), self.target)

    def _become_idle(self):
        """Transition to idle and release the rider's route."""
        self.state = STATE_IDLE
        self.target = None
        self.route = []
        self.special_case = not PathPlanner.is_street(self.x, self.y)

    def _start_pickup(self):
        """Begin the pickup of the first assigned order (idle -> picking up)."""
        order = self.orders[0]
        order.mark_picking_up()
        self.state = STATE_PICKING_UP
        self._record("accepted_order", order.id)
        self._set_target(order.res_pos)

    def _arrive_at_merchant(self):
        """Handle arrival at the restaurant (picking up -> delivering)."""
        order = self.orders[0]
        order.mark_delivering(_current_tick())
        self.state = STATE_DELIVERING
        self._record("arrived_at_merchant", order.id)
        self._set_target(order.cus_pos)

    def _deliver_current_order(self):
        """Complete the active order and release it from the rider.

        If more orders are queued the rider starts the next pickup; otherwise
        it becomes idle.
        """
        order = self.orders.pop(0)
        order.mark_completed(_current_tick())
        self._record("delivered_to_customer", order.id)
        logger.info(
            "Order #%d delivered by rider #%d at tick %d",
            order.id, self.rider_id, _current_tick(),
        )
        if self.orders:
            self._start_pickup()
        else:
            self._become_idle()

    def repair_state(self):
        """Repair a state that contradicts the order list.

        Returns:
            bool: True if the state was changed.
        """
        if self.orders and self.state == STATE_IDLE:
            self._start_pickup()
            return True
        if not self.orders and self.state != STATE_IDLE:
            self._become_idle()
            return True
        return False

    # ------------------------------------------------------------------ #
    # Movement
    # ------------------------------------------------------------------ #
    def _advance(self):
        """Move up to ``speed`` units along the planned route.

        Each waypoint is axis-aligned from the previous position, so movement
        is strictly horizontal or vertical (right-angle turns at corners).
        """
        remaining = self.speed
        while remaining > 0 and self.route:
            wx, wy = self.route[0]
            dx = wx - self.x
            dy = wy - self.y
            dist = abs(dx) + abs(dy)
            if dist == 0:
                self.route.pop(0)
                continue
            if dist <= remaining:
                self.x, self.y = wx, wy
                remaining -= dist
                self.route.pop(0)
            else:
                step_x = max(-remaining, min(remaining, dx))
                self.x += step_x
                remaining -= abs(step_x)
                step_y = max(-remaining, min(remaining, dy))
                self.y += step_y
                remaining -= abs(step_y)
        self.special_case = not PathPlanner.is_street(self.x, self.y)

    def move(self):
        """Advance the rider by one tick.

        Performs, in order: idle -> picking up when an order is present,
        movement along the route, then the arrival transitions when the
        destination is reached (picking up -> delivering, delivering -> idle).
        """
        if not self.orders:
            if self.state != STATE_IDLE:
                self._become_idle()
            return

        if self.state == STATE_IDLE:
            self._start_pickup()

        self._advance()

        if self.target is None or self.position() != self.target:
            return
        if self.state == STATE_PICKING_UP:
            self._arrive_at_merchant()
        elif self.state == STATE_DELIVERING:
            self._deliver_current_order()
