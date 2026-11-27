"""Rider model: state machine, movement along streets and event logging.

Rider states:
    0 = idle, 1 = picking up (heading to restaurant), 2 = delivering.

Log events recorded in ``Rider.log``:
    "spawn", "accepted_order", "arrived_at_merchant", "delivered_to_customer"
"""

import logging

import globalvar
from path_planner import PathPlanner

logger = logging.getLogger(__name__)

IDLE = 0
PICKING_UP = 1
DELIVERING = 2
STATE_NAMES = {IDLE: "idle", PICKING_UP: "picking up", DELIVERING: "delivering"}

DEFAULT_SPEED = 20
SPAWN_X = 400
SPAWN_Y = 400

ACTIVE_STATUSES = ("assigned", "picking_up", "delivering")
IN_PROGRESS_STATUSES = ("picking_up", "delivering")


class Rider:
    """A delivery rider that moves on the street grid and serves orders.

    Attributes:
        rider_id (int): Unique identifier.
        x, y (int): Current location.
        speed (int): Units moved per tick.
        state (int): 0 idle, 1 picking up, 2 delivering.
        orders (list[Order]): Assigned orders, including completed history.
        special_case (bool): Flag set when an unusual condition was repaired.
        log (list[dict]): Status change records.
    """

    def __init__(self, rider_id, x=SPAWN_X, y=SPAWN_Y, speed=DEFAULT_SPEED):
        """Create a rider and log its spawn event.

        Args:
            rider_id: Unique rider identifier.
            x: Initial x coordinate (default 400).
            y: Initial y coordinate (default 400).
            speed: Movement speed in units per tick (default 20).
        """
        self.rider_id = int(rider_id)
        self.x = int(x)
        self.y = int(y)
        self.speed = int(speed)
        self.state = IDLE
        self.orders = []
        self.special_case = False
        self.log = []
        self._record("spawn", None)

    # ------------------------------------------------------------------
    # Properties and queries
    # ------------------------------------------------------------------
    @property
    def position(self):
        """Current ``(x, y)`` location."""
        return (self.x, self.y)

    @property
    def state_name(self):
        """Human-readable state label."""
        return STATE_NAMES.get(self.state, "unknown")

    def active_orders(self):
        """Orders that are not yet completed, in queue order.

        Returns:
            list[Order]: Active orders.
        """
        return [o for o in self.orders if o.status in ACTIVE_STATUSES]

    def active_order_count(self):
        """Number of active (not completed) orders.

        Returns:
            int: Count of active orders.
        """
        return len(self.active_orders())

    def is_idle(self):
        """Whether the rider is free to receive work.

        Returns:
            bool: True when state is idle and no active orders exist.
        """
        return self.state == IDLE and self.active_order_count() == 0

    def current_order(self):
        """The order currently being picked up or delivered.

        Returns:
            Order | None: The in-progress order, if any.
        """
        for order in self.orders:
            if order.status in IN_PROGRESS_STATUSES:
                return order
        return None

    def remaining_waypoints(self):
        """Ordered waypoints still to visit for all active orders.

        Returns:
            list[tuple[int, int]]: Restaurant/customer points to visit.
        """
        points = []
        for order in self.active_orders():
            if order.status == "delivering":
                points.append(order.cus_pos)
            else:
                points.extend([order.res_pos, order.cus_pos])
        return points

    # ------------------------------------------------------------------
    # State machine and movement
    # ------------------------------------------------------------------
    def move(self):
        """Advance the rider by one tick.

        Handles state transitions:
            idle -> picking up when an assigned order exists,
            picking up -> delivering on reaching the restaurant,
            delivering -> idle (then picking up the next queued order)
            on reaching the customer.
        """
        tick = self._tick()
        if self.state == IDLE and not self._accept_next(tick):
            return

        order = self.current_order()
        if order is None:
            self._repair(tick)
            return

        self._sync_state(order)
        target = self._target(order)
        if self.position != target:
            self.x, self.y = PathPlanner.step_towards(
                self.x, self.y, target[0], target[1], self.speed
            )
        if self.position == target:
            self._on_arrival(order, tick)

    def to_dict(self):
        """Serialize the rider to a JSON-compatible dict.

        Returns:
            dict: Rider attributes including order history.
        """
        return {
            "rider_id": self.rider_id,
            "x": self.x,
            "y": self.y,
            "speed": self.speed,
            "state": self.state,
            "special_case": self.special_case,
            "orders": [o.to_dict() for o in self.orders],
        }

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------
    @staticmethod
    def _tick():
        """Current simulation tick from the global store."""
        return globalvar.get_value("tick", 0)

    def _record(self, event, order_id):
        """Append a status-change record to the rider log.

        Args:
            event: Event name.
            order_id: Related order id or None.
        """
        self.log.append({
            "event": event,
            "order_id": order_id,
            "time": self._tick(),
            "rider_id": self.rider_id,
            "x": self.x,
            "y": self.y,
            "state": self.state,
        })

    def _accept_next(self, tick):
        """Accept the first queued order if the rider is able to start it.

        Args:
            tick: Current tick (used for logging consistency).

        Returns:
            bool: True when an order was accepted.
        """
        for order in self.orders:
            if order.status == "assigned":
                order.status = "picking_up"
                self.state = PICKING_UP
                self._record("accepted_order", order.id)
                return True
        return False

    def _sync_state(self, order):
        """Make the rider state agree with its in-progress order.

        Args:
            order: The in-progress order.
        """
        if order.status == "picking_up":
            self.state = PICKING_UP
        elif order.status == "delivering":
            self.state = DELIVERING

    def _target(self, order):
        """Destination for the given in-progress order.

        Args:
            order: The in-progress order.

        Returns:
            tuple[int, int]: Restaurant point when picking up, else customer.
        """
        return order.res_pos if order.status == "picking_up" else order.cus_pos

    def _on_arrival(self, order, tick):
        """Handle arriving at the restaurant or the customer.

        Args:
            order: The in-progress order.
            tick: Current tick.
        """
        if order.status == "picking_up":
            order.status = "delivering"
            self.state = DELIVERING
            self._record("arrived_at_merchant", order.id)
        else:
            order.complete(tick)
            self.state = IDLE
            self._record("delivered_to_customer", order.id)
            self._accept_next(tick)

    def _repair(self, tick):
        """Recover from an inconsistent state (state without an order).

        Args:
            tick: Current tick.
        """
        logger.warning("Rider %s inconsistent state; repairing", self.rider_id)
        self.special_case = True
        self.state = IDLE
        self._accept_next(tick)
