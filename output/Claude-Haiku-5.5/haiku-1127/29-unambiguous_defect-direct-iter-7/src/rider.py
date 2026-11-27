"""Rider model: state machine, street movement and order execution."""

import logging
import random

import globalvar
import grid
from path_planner import PathPlanner

IDLE = 0
PICKING_UP = 1
DELIVERING = 2

STATE_NAMES = {IDLE: "idle", PICKING_UP: "picking up", DELIVERING: "delivering"}
SPEED_CHOICES = (50, 100)

logger = logging.getLogger("dispatch.rider")


class Rider:
    """A delivery rider that moves along streets and executes orders.

    Attributes:
        rider_id: Unique integer identifier.
        x: Current horizontal coordinate.
        y: Current vertical coordinate.
        speed: Movement speed in units per tick.
        state: 0 idle, 1 picking up, 2 delivering.
        orders: Queue of assigned orders; ``orders[0]`` is the active order.
        special_case: True when the current target lies on the same row or
            column as the rider (straight-line movement).
        log: List of status-change dictionaries with keys including
            "event" and "order_id".
        distance_travelled: Total distance covered in map units.
    """

    def __init__(self, rider_id, x=None, y=None, speed=None):
        """Create a rider and place it on a street intersection.

        Args:
            rider_id: Unique identifier for the rider.
            x: Optional starting x coordinate (snapped to a street).
            y: Optional starting y coordinate (snapped to a street).
            speed: Optional speed in units per tick.
        """
        if x is None or y is None:
            x = random.randrange(grid.LATTICE_DIM) * grid.CELL_SIZE
            y = random.randrange(grid.LATTICE_DIM) * grid.CELL_SIZE
        x, y = grid.snap_to_grid(x, y)
        self.rider_id = rider_id
        self.x = x
        self.y = y
        self.speed = int(speed) if speed else random.choice(SPEED_CHOICES)
        self.state = IDLE
        self.orders = []
        self.special_case = False
        self.log = []
        self.distance_travelled = 0
        self._record("spawn", None)

    @property
    def position(self):
        """Return the current position as a tuple ``(x, y)``."""
        return self.x, self.y

    @property
    def state_name(self):
        """Return a human-readable name for the current state."""
        return STATE_NAMES.get(self.state, "unknown")

    def is_available(self):
        """Return True if the rider is idle and has no assigned orders."""
        return self.state == IDLE and not self.orders

    def current_target(self):
        """Return the point the rider is heading to, or None if no orders."""
        if not self.orders:
            return None
        order = self.orders[0]
        if self.state == DELIVERING:
            return order.cus_pos
        return order.res_pos

    def _is_straight_line(self, target):
        """Return True if the target shares the rider's row or column."""
        return self.x == target[0] or self.y == target[1]

    def move(self):
        """Advance the rider by one tick and apply state transitions.

        Transitions:
            Idle with an order -> Picking up (event "accepted_order").
            Picking up, arrived at restaurant -> Delivering
                (event "arrived_at_merchant").
            Delivering, arrived at customer -> Idle
                (event "delivered_to_customer"); the order is completed and
                removed from the rider's queue.
        """
        now = int(globalvar.get_value("time", 0))
        if not self.orders:
            if self.state != IDLE:
                logger.warning("rider %s had state %s without orders; resetting",
                               self.rider_id, self.state)
                self.state = IDLE
            self.special_case = False
            return

        order = self.orders[0]
        if self.state == IDLE:
            self.state = PICKING_UP
            order.mark_accepted(now)
            self._record("accepted_order", order.id)
            return

        target = self.current_target()
        self.special_case = self._is_straight_line(target)
        nx, ny, _ = PathPlanner.step_towards(self.x, self.y, target[0], target[1],
                                             self.speed)
        self.distance_travelled += grid.manhattan(self.position, (nx, ny))
        self.x, self.y = nx, ny
        if self.position != tuple(target):
            return

        if self.state == PICKING_UP:
            self.state = DELIVERING
            order.mark_picked_up(now)
            self._record("arrived_at_merchant", order.id)
        else:
            self.orders.pop(0)
            order.mark_completed(now)
            self.state = IDLE
            self.special_case = False
            self._record("delivered_to_customer", order.id)

    def _record(self, event, order_id, **extra):
        """Append a status-change entry to the rider log.

        Args:
            event: Event name such as "spawn" or "accepted_order".
            order_id: Related order ID, or None.
            **extra: Additional fields to store with the entry.
        """
        entry = {
            "event": event,
            "order_id": order_id,
            "time": int(globalvar.get_value("time", 0)),
            "rider_id": self.rider_id,
            "x": self.x,
            "y": self.y,
            "state": self.state,
        }
        entry.update(extra)
        self.log.append(entry)
        logger.debug("rider %s event %s order %s", self.rider_id, event, order_id)

    def to_dict(self):
        """Return a JSON-serialisable representation of the rider."""
        return {
            "rider_id": self.rider_id,
            "x": self.x,
            "y": self.y,
            "speed": self.speed,
            "state": self.state,
            "order_ids": [o.id for o in self.orders],
            "special_case": self.special_case,
            "distance_travelled": self.distance_travelled,
            "log": list(self.log),
        }
