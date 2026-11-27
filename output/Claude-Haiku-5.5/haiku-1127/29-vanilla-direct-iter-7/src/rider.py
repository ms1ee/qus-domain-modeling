"""Rider model: state machine, movement and event logging."""

import logging

import globalvar
from constants import (
    MAX_BLOCKED_WAIT,
    MAP_SIZE,
    ORDER_ASSIGNED,
    ORDER_PICKING_UP,
    RIDER_SPEED,
    RIDER_START_X,
    RIDER_START_Y,
    STATE_DELIVERING,
    STATE_IDLE,
    STATE_PICKING_UP,
)
from path_planner import PathPlanner

logger = logging.getLogger(__name__)


class Rider:
    """A delivery rider that moves along the street grid and serves orders.

    Attributes:
        rider_id (int): Unique identifier.
        x (int), y (int): Current position.
        speed (int): Units moved per tick.
        state (int): 0 idle, 1 picking up, 2 delivering.
        orders (list[Order]): Assigned orders; index 0 is the current order.
        special_case (bool): Flag set while the rider is waiting on a blocked tile.
        log (list[dict]): Status change history. Each entry has keys
            "event", "order_id", "time", "rider_id", "x", "y", "state".
        distance_travelled (int): Total Manhattan distance moved.
        wait_ticks (int): Consecutive ticks spent waiting on a blocked tile.
    """

    def __init__(self, rider_id, x=RIDER_START_X, y=RIDER_START_Y, speed=RIDER_SPEED):
        """Create a new idle rider and log its spawn event.

        Args:
            rider_id: Unique integer identifier.
            x: Initial X coordinate (default 435).
            y: Initial Y coordinate (default 385).
            speed: Units per tick (default 10).

        Raises:
            ValueError: If the identifier or speed is invalid.
        """
        if isinstance(rider_id, bool) or not isinstance(rider_id, int):
            raise ValueError("rider_id must be an integer")
        if speed < 1:
            raise ValueError("speed must be at least 1")
        self.rider_id = rider_id
        self.x = int(x)
        self.y = int(y)
        self.speed = int(speed)
        self.state = STATE_IDLE
        self.orders = []
        self.special_case = False
        self.log = []
        self.distance_travelled = 0
        self.wait_ticks = 0
        self._log("spawn", None)

    def __repr__(self):
        return (f"Rider(id={self.rider_id}, pos=({self.x},{self.y}), "
                f"state={self.state}, orders={len(self.orders)})")

    @property
    def position(self):
        """Current (x, y) position as a tuple."""
        return self.x, self.y

    def current_order(self):
        """Return the order currently being served, or None."""
        return self.orders[0] if self.orders else None

    def current_target(self):
        """Return the target point for the rider's current state, or None.

        Idle riders have no target. Picking-up riders head to the restaurant;
        delivering riders head to the customer.
        """
        order = self.current_order()
        if order is None or self.state == STATE_IDLE:
            return None
        if self.state == STATE_PICKING_UP:
            return order.res_pos
        if self.state == STATE_DELIVERING:
            return order.cus_pos
        return None

    def _now(self):
        return globalvar.get_value("tick", 0)

    def _log(self, event, order_id):
        """Append a status-change record to the rider log."""
        entry = {
            "event": event,
            "order_id": order_id,
            "time": self._now(),
            "rider_id": self.rider_id,
            "x": self.x,
            "y": self.y,
            "state": self.state,
        }
        self.log.append(entry)
        logger.debug("Rider %s event=%s order=%s", self.rider_id, event, order_id)

    def _other_rider_at(self, x, y):
        """Return True if another rider occupies (x, y)."""
        for other in globalvar.get_value("riders", []) or []:
            if other is not self and other.x == x and other.y == y:
                return True
        return False

    def _optimize_queue(self):
        """Greedily reorder not-yet-picked-up orders by nearest restaurant.

        This is the multi-destination optimisation: starting from the rider's
        current position, the nearest restaurant is served first, then the
        next nearest from there.
        """
        pending = [o for o in self.orders if o.status == ORDER_ASSIGNED]
        if len(pending) <= 1:
            return
        in_progress = [o for o in self.orders if o.status != ORDER_ASSIGNED]
        ordered = []
        cx, cy = self.x, self.y
        remaining = list(pending)
        while remaining:
            nxt = min(
                remaining,
                key=lambda o: (abs(o.res_pos[0] - cx) + abs(o.res_pos[1] - cy), o.id),
            )
            remaining.remove(nxt)
            ordered.append(nxt)
            cx, cy = nxt.res_pos
        self.orders = in_progress + ordered

    def _start_pickup(self):
        """Transition Idle -> Picking Up for the next queued order."""
        self._optimize_queue()
        self.state = STATE_PICKING_UP
        order = self.orders[0]
        order.status = ORDER_PICKING_UP
        self._log("accepted_order", order.id)

    def _step_towards(self, target):
        """Advance one tick toward ``target`` with blocked-tile handling."""
        tx, ty = target
        nx, ny = PathPlanner.next_position(self.x, self.y, tx, ty, self.speed)
        if (nx, ny) == (self.x, self.y):
            return
        if self._other_rider_at(nx, ny) and self.wait_ticks < MAX_BLOCKED_WAIT:
            # Conflict avoidance: yield the tile for a few ticks.
            self.wait_ticks += 1
            self.special_case = True
            return
        # Deadlock avoidance: after MAX_BLOCKED_WAIT ticks the rider proceeds.
        self.special_case = (nx == tx and ny != ty) or (ny == ty and nx != tx)
        self.wait_ticks = 0
        self.distance_travelled += abs(nx - self.x) + abs(ny - self.y)
        self.x, self.y = nx, ny
        self.x = min(max(self.x, 0), MAP_SIZE)
        self.y = min(max(self.y, 0), MAP_SIZE)

    def _handle_arrival(self):
        """Handle reaching the current target (restaurant or customer)."""
        order = self.current_order()
        if order is None:
            self.state = STATE_IDLE
            return
        if self.state == STATE_PICKING_UP:
            self.state = STATE_DELIVERING
            order.mark_picked_up(self._now())
            self._log("arrived_at_merchant", order.id)
        elif self.state == STATE_DELIVERING:
            self.orders.pop(0)
            order.mark_completed(self._now())
            self.state = STATE_IDLE
            self._log("delivered_to_customer", order.id)

    def move(self):
        """Advance the rider by one tick.

        Handles the Idle -> Picking Up transition when an order is queued,
        moves toward the current target, and performs the Picking Up ->
        Delivering and Delivering -> Idle transitions on arrival.
        """
        if self.state == STATE_IDLE:
            if not self.orders:
                return
            self._start_pickup()
        target = self.current_target()
        if target is None:
            return
        self._step_towards(target)
        if (self.x, self.y) == target:
            self._handle_arrival()
