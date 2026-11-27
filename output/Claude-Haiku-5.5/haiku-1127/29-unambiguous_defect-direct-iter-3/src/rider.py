"""Rider model: state machine, street movement and event logging.

State machine (derived from the rider's order list):
    idle (0)        -> no active orders
    picking up (1)  -> at least one order assigned but not yet collected
    delivering (2)  -> all active orders collected, heading to customers

Multiple orders are served with a greedy nearest-stop policy: the rider
always heads for the nearest pending stop (restaurant of an assigned order or
customer of a carried order). Deliveries win ties so food is not held longer
than necessary.
"""

import logging
import random

import config
import globalvar
import grid
from order_model import STATUS_ASSIGNED, STATUS_COMPLETED, STATUS_PICKED_UP
from path_planner import PathPlanner

logger = logging.getLogger("dispatch.rider")

STATE_NAMES = {
    config.STATE_IDLE: "idle",
    config.STATE_PICKING_UP: "picking up",
    config.STATE_DELIVERING: "delivering",
}

EVENT_SPAWN = "spawn"
EVENT_ACCEPTED = "accepted_order"
EVENT_ARRIVED_MERCHANT = "arrived_at_merchant"
EVENT_DELIVERED = "delivered_to_customer"
EVENT_STATE_CHANGE = "state_change"


class Rider:
    """A delivery rider that moves along streets and serves orders.

    Attributes:
        rider_id: Unique identifier.
        x, y: Current position (integers, always on a street).
        speed: Movement in units per tick.
        state: 0 idle, 1 picking up, 2 delivering.
        orders: Active orders (assigned or carried).
        special_case: True while directly above/below the current target.
        log: List of event dictionaries (keys include "event" and "order_id").
        distance_traveled: Total units travelled since spawn.
    """

    def __init__(self, rider_id, x=None, y=None, speed=None):
        """Create a rider on a street.

        Args:
            rider_id: Unique integer identifier.
            x: Optional starting x; random road point when omitted.
            y: Optional starting y; random road point when omitted.
            speed: Optional units per tick; random within configured range.

        Raises:
            ValueError: If the supplied coordinates are out of range.
        """
        self.rider_id = int(rider_id)
        if x is None or y is None:
            x, y = self.random_road_point()
        if not (grid.is_valid_coordinate(x) and grid.is_valid_coordinate(y)):
            raise ValueError(f"Rider start position ({x},{y}) is out of range")
        if not grid.is_on_road(x, y):
            x, y = grid.snap_to_road(x, y)
        self.x = x
        self.y = y
        if speed is None:
            speed = random.randint(config.RIDER_SPEED_MIN, config.RIDER_SPEED_MAX)
        self.speed = max(1, int(speed))
        self.state = config.STATE_IDLE
        self.orders = []
        self.special_case = False
        self.log = []
        self.distance_traveled = 0
        self._acknowledged = set()
        self._log_event(EVENT_SPAWN, None)

    @staticmethod
    def random_road_point():
        """Pick a random integer point lying on a street.

        Returns:
            tuple[int, int]: A road point within the map.
        """
        span = config.MAP_SIZE
        step = config.CELL_SIZE
        if random.random() < 0.5:
            y = random.randrange(0, span + 1, step)
            x = random.randint(0, span)
        else:
            x = random.randrange(0, span + 1, step)
            y = random.randint(0, span)
        return x, y

    @property
    def position(self):
        """Current ``(x, y)`` position."""
        return (self.x, self.y)

    @property
    def is_idle(self):
        """True when the rider has no active orders."""
        return not self.orders

    @property
    def state_name(self):
        """Human-readable state label."""
        return STATE_NAMES.get(self.state, "unknown")

    def refresh_state(self):
        """Register newly assigned orders and recompute the rider state.

        Safe to call at any time; it is idempotent.
        """
        self._acknowledge_new_orders()
        self._update_state()

    def move(self):
        """Advance the rider by one tick.

        Processes pickups and deliveries at the current position, moves one
        movement step toward the nearest pending stop, processes arrivals
        again, and refreshes the state machine.
        """
        self.refresh_state()
        self._process_arrivals()
        target = self._choose_target()
        if target is not None:
            tx, ty = target
            nx, ny, special = PathPlanner.next_step(self.x, self.y, tx, ty, self.speed)
            self.distance_traveled += abs(nx - self.x) + abs(ny - self.y)
            self.x, self.y = nx, ny
            self.special_case = special
            self._process_arrivals()
        else:
            self.special_case = False
        self.refresh_state()

    def to_dict(self):
        """Return a JSON-serializable snapshot of the rider.

        Returns:
            dict: Rider attributes including active order IDs.
        """
        return {
            "rider_id": self.rider_id,
            "x": self.x,
            "y": self.y,
            "speed": self.speed,
            "state": self.state,
            "order_ids": [order.id for order in self.orders],
            "special_case": self.special_case,
            "distance_traveled": self.distance_traveled,
        }

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------
    def _log_event(self, event, order_id, **extra):
        """Append an event entry to the rider log, trimming old entries."""
        entry = {
            "event": event,
            "order_id": order_id,
            "time": globalvar.get_value("tick", 0),
            "rider_id": self.rider_id,
            "x": self.x,
            "y": self.y,
            "state": self.state,
        }
        entry.update(extra)
        self.log.append(entry)
        overflow = len(self.log) - config.MAX_RIDER_LOG
        if overflow > 0:
            del self.log[:overflow]

    def _acknowledge_new_orders(self):
        """Log an accepted_order event for every newly assigned order."""
        for order in self.orders:
            if order.status == STATUS_ASSIGNED and order.id not in self._acknowledged:
                self._acknowledged.add(order.id)
                self._log_event(EVENT_ACCEPTED, order.id)

    def _update_state(self):
        """Derive the state from the order list and log any transition."""
        if any(order.status == STATUS_ASSIGNED for order in self.orders):
            new_state = config.STATE_PICKING_UP
        elif self.orders:
            new_state = config.STATE_DELIVERING
        else:
            new_state = config.STATE_IDLE
        if new_state != self.state:
            old_state = self.state
            self.state = new_state
            self._log_event(EVENT_STATE_CHANGE, None, from_state=old_state, to_state=new_state)

    def _choose_target(self):
        """Select the nearest pending stop, preferring deliveries on ties.

        Returns:
            tuple[int, int] | None: Target intersection, or None if no stops.
        """
        here = self.position
        best = None
        for order in self.orders:
            if order.status == STATUS_ASSIGNED:
                candidate = (grid.manhattan(here, order.restaurant_node), 1, order.restaurant_node)
            elif order.status == STATUS_PICKED_UP:
                candidate = (grid.manhattan(here, order.customer_node), 0, order.customer_node)
            else:
                continue
            if best is None or candidate[:2] < best[:2]:
                best = candidate
        return None if best is None else best[2]

    def _process_arrivals(self):
        """Handle pickups and deliveries that occur at the current position."""
        here = self.position
        tick = globalvar.get_value("tick", 0)

        for order in list(self.orders):
            if order.status == STATUS_ASSIGNED and order.restaurant_node == here:
                order.mark_picked_up(tick)
                self._log_event(EVENT_ARRIVED_MERCHANT, order.id)

        for order in list(self.orders):
            if order.status == STATUS_PICKED_UP and order.customer_node == here:
                order.mark_completed(tick)
                self.orders.remove(order)
                self._acknowledged.discard(order.id)
                self._log_event(EVENT_DELIVERED, order.id)
                self._record_completion(order)

    def _record_completion(self, order):
        """Store a completed order in the history and credit the delivery fee."""
        history = globalvar.get_value("order_history")
        if history is None:
            history = []
            globalvar.set_value("order_history", history)
        history.append(order)
        funds = globalvar.get_value("funds", 0)
        globalvar.set_value("funds", funds + config.DELIVERY_FEE)
        logger.info(
            "Order %s delivered by rider %s at tick %s",
            order.id,
            self.rider_id,
            order.complete_tick,
        )


__all__ = [
    "Rider",
    "STATE_NAMES",
    "EVENT_SPAWN",
    "EVENT_ACCEPTED",
    "EVENT_ARRIVED_MERCHANT",
    "EVENT_DELIVERED",
    "EVENT_STATE_CHANGE",
    "STATUS_COMPLETED",
]
