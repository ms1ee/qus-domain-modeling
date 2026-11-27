"""Rider model: state machine, movement and order execution.

Riders follow a three-state life cycle::

    IDLE (0) --new order--> PICKING_UP (1) --arrive at restaurant-->
    DELIVERING (2) --arrive at customer--> IDLE (0)

Movement is performed one tick at a time by :meth:`Rider.move`.  Routes come
from :class:`path_planner.PathPlanner` and always run along streets first.
Riders never block each other, so no deadlock can occur.
"""

import logging

import globalvar
from order_model import STATUS_DELIVERING, STATUS_PICKING_UP
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

INITIAL_X = 435
INITIAL_Y = 385
DEFAULT_SPEED = 10


class Rider:
    """A delivery rider that moves on the grid and executes orders.

    Attributes:
        rider_id (int): unique identifier.
        x (int): current x coordinate.
        y (int): current y coordinate.
        speed (int): movement budget in units per tick.
        state (int): 0 idle, 1 picking up, 2 delivering.
        orders (list[Order]): assigned orders; index 0 is the active order.
        special_case (bool): True while the rider is directly above or below
            its target and must travel straight along one street.
        log (list[dict]): status change history.  Each entry contains the
            keys ``event`` and ``order_id`` plus ``time``, ``x``, ``y``,
            ``state`` and ``rider_id``.
        target (tuple | None): current destination.
        waypoints (list[tuple]): remaining points on the planned route.
        distance_travelled (int): total units moved.
    """

    def __init__(self, rider_id):
        """Create a rider on the road at the initial position.

        Args:
            rider_id (int): unique identifier assigned by the system.
        """
        self.rider_id = int(rider_id)
        self.x = INITIAL_X
        self.y = INITIAL_Y
        self.speed = DEFAULT_SPEED
        self.state = STATE_IDLE
        self.orders = []
        self.special_case = False
        self.log = []
        self.target = None
        self.waypoints = []
        self.distance_travelled = 0
        self._planner = PathPlanner()
        self._record("spawn", None)

    def position(self):
        """Return the current position as ``(x, y)``."""
        return (self.x, self.y)

    def is_idle(self):
        """Return True when the rider is available for new orders."""
        return self.state == STATE_IDLE

    def move(self):
        """Advance the rider by one tick.

        Performs state transitions (and records their log entries) as well
        as movement along the planned route.
        """
        if self.state == STATE_IDLE:
            if not self.orders:
                return
            first = self.orders[0]
            self.state = STATE_PICKING_UP
            first.status = STATUS_PICKING_UP
            self._record("accepted_order", first.id)
            self._set_target(first.res_pos)
        elif not self.orders:
            self._become_idle()
            return

        self._advance()
        if (self.x, self.y) != self.target:
            return
        if self.state == STATE_PICKING_UP:
            self._arrive_at_merchant()
        elif self.state == STATE_DELIVERING:
            self._deliver_current_order()

    def recover(self):
        """Re-synchronise the rider after an error.

        Clears the route and rebuilds the target from the order list.  Riders
        without orders are returned to the idle state.
        """
        logger.warning("Recovering rider %d", self.rider_id)
        self.waypoints = []
        self.target = None
        if not self.orders:
            self._become_idle()
            return
        order = self.orders[0]
        if self.state == STATE_DELIVERING:
            order.status = STATUS_DELIVERING
            self._set_target(order.cus_pos)
        else:
            self.state = STATE_PICKING_UP
            order.status = STATUS_PICKING_UP
            self._set_target(order.res_pos)

    def to_dict(self):
        """Return a JSON-serialisable snapshot of the rider.

        Returns:
            dict: rider attributes, assigned order IDs and history log.
        """
        return {
            "rider_id": self.rider_id,
            "x": self.x,
            "y": self.y,
            "speed": self.speed,
            "state": self.state,
            "special_case": self.special_case,
            "order_ids": [order.id for order in self.orders],
            "log": list(self.log),
        }

    def _arrive_at_merchant(self):
        """Switch from picking up to delivering once the restaurant is reached."""
        order = self.orders[0]
        self.state = STATE_DELIVERING
        order.status = STATUS_DELIVERING
        self._record("arrived_at_merchant", order.id)
        self._set_target(order.cus_pos)

    def _deliver_current_order(self):
        """Complete the active order and release the rider or start the next one."""
        order = self.orders.pop(0)
        order.complete(globalvar.current_tick())
        self._record("delivered_to_customer", order.id)
        if self.orders:
            next_order = self.orders[0]
            self.state = STATE_PICKING_UP
            next_order.status = STATUS_PICKING_UP
            self._record("accepted_order", next_order.id)
            self._set_target(next_order.res_pos)
        else:
            self._become_idle()

    def _become_idle(self):
        """Reset the rider to the idle state with no active route."""
        self.state = STATE_IDLE
        self.target = None
        self.waypoints = []
        self.special_case = False

    def _set_target(self, target):
        """Plan a route from the current position to ``target``.

        Args:
            target (tuple): destination ``(x, y)``.
        """
        self.target = (int(target[0]), int(target[1]))
        route = self._planner.plan((self.x, self.y), self.target, self.speed)
        self.waypoints = [(p.x, p.y) for p in route.points[1:]]
        self.special_case = self._planner.is_directly_above_or_below(
            (self.x, self.y), self.target
        )

    def _advance(self):
        """Spend the per-tick movement budget along the planned waypoints.

        Movement is axis-aligned: each step changes only one coordinate.
        """
        budget = self.speed
        while budget > 0 and self.waypoints:
            tx, ty = self.waypoints[0]
            dx = tx - self.x
            dy = ty - self.y
            if dx == 0 and dy == 0:
                self.waypoints.pop(0)
                continue
            if dx != 0:
                step = min(budget, abs(dx))
                self.x += step if dx > 0 else -step
            else:
                step = min(budget, abs(dy))
                self.y += step if dy > 0 else -step
            budget -= step
            self.distance_travelled += step
            if (self.x, self.y) == (tx, ty):
                self.waypoints.pop(0)

    def _record(self, event, order_id):
        """Append a status change entry to the rider log.

        Args:
            event (str): event name, e.g. ``"accepted_order"``.
            order_id (int | None): related order ID.
        """
        entry = {
            "event": event,
            "order_id": order_id,
            "time": globalvar.current_tick(),
            "x": self.x,
            "y": self.y,
            "state": self.state,
            "rider_id": self.rider_id,
        }
        self.log.append(entry)
        logger.debug("Rider %d: %s order=%s", self.rider_id, event, order_id)
