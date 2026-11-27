"""Rider model: state machine, movement, and event logging."""

import logging

import globalvar
from path_planner import PathPlanner

logger = logging.getLogger("dispatch.rider")

STATE_IDLE = 0
STATE_PICKING_UP = 1
STATE_DELIVERING = 2

STATE_NAMES = {
    STATE_IDLE: "idle",
    STATE_PICKING_UP: "picking up",
    STATE_DELIVERING: "delivering",
}

DEFAULT_SPEED = 50
DEFAULT_DELIVERY_FEE = 30


def _config_value(key, default):
    """Read a configuration value, falling back to ``default``."""
    config = globalvar.get_value("config") or {}
    return config.get(key, default)


def _current_tick():
    """Return the current simulated tick."""
    return globalvar.get_value("tick", 0)


class Rider:
    """A delivery rider that moves on the street grid and serves orders.

    Attributes:
        rider_id (int): Unique identifier.
        x, y (int): Current coordinates.
        speed (int): Movement speed in units per tick.
        state (int): 0 = idle, 1 = picking up, 2 = delivering.
        orders (list): Assigned orders; ``orders[0]`` is the active one.
        special_case (bool): True while directly above/below the target.
        log (list[dict]): Status change records with keys ``time``,
            ``event``, ``order_id``, ``x``, ``y``, ``state`` and ``rider_id``.
    """

    def __init__(self, rider_id):
        """Create a rider at a random road position in idle state.

        Args:
            rider_id: Unique integer identifier for the rider.
        """
        self.rider_id = rider_id
        self.x, self.y = PathPlanner.random_road_point()
        self.speed = int(_config_value("rider_speed", DEFAULT_SPEED))
        self.state = STATE_IDLE
        self.orders = []
        self.special_case = False
        self.log = []
        self._record("spawn", None)

    @property
    def position(self):
        """Return the current position as ``(x, y)``."""
        return (self.x, self.y)

    @property
    def state_name(self):
        """Return a human readable state name."""
        return STATE_NAMES.get(self.state, "unknown")

    def _record(self, event, order_id):
        """Append a status change entry to the rider log."""
        entry = {
            "time": _current_tick(),
            "event": event,
            "order_id": order_id,
            "x": self.x,
            "y": self.y,
            "state": self.state,
            "rider_id": self.rider_id,
        }
        self.log.append(entry)
        logger.debug("Rider %s t=%s %s order=%s", self.rider_id, entry["time"], event, order_id)

    def move(self):
        """Advance the rider by one tick.

        Handles the state transitions:
            * Idle -> Picking up when an order is assigned ("accepted_order").
            * Picking up -> Delivering on reaching the restaurant
              ("arrived_at_merchant").
            * Delivering -> Idle on reaching the customer
              ("delivered_to_customer").
        """
        if not self.orders:
            self.state = STATE_IDLE
            self.special_case = False
            return

        order = self.orders[0]
        if self.state == STATE_IDLE:
            self.state = STATE_PICKING_UP
            order.status = "picking_up"
            self._record("accepted_order", order.id)

        target = order.restaurant_pos if self.state == STATE_PICKING_UP else order.customer_pos
        self._advance_toward(target)

        if self.position != target:
            return

        if self.state == STATE_PICKING_UP:
            self.state = STATE_DELIVERING
            order.status = "delivering"
            self._record("arrived_at_merchant", order.id)
        else:
            self._deliver(order)

    def _advance_toward(self, target):
        """Move up to ``speed`` units along the street grid toward ``target``.

        Riders never block each other, so movement cannot deadlock. A guard
        stops movement if the planner ever reports no progress.
        """
        tx, ty = target
        budget = self.speed
        while budget > 0 and self.position != target:
            nx, ny = PathPlanner.next_step(self.x, self.y, tx, ty)
            if (nx, ny) == self.position:
                logger.warning("Rider %s made no progress toward %s", self.rider_id, target)
                break
            self.x, self.y = nx, ny
            budget -= 1
        self.special_case = self.position != target and self.x == tx

    def _deliver(self, order):
        """Complete the active order, release the rider, and credit the fee."""
        self.orders.pop(0)
        order.complete(_current_tick())
        fee = int(_config_value("delivery_fee", DEFAULT_DELIVERY_FEE))
        globalvar.set_value("funds", globalvar.get_value("funds", 0) + fee)
        self.state = STATE_IDLE
        self.special_case = False
        self._record("delivered_to_customer", order.id)

    def to_dict(self):
        """Return a JSON-serializable snapshot of the rider."""
        return {
            "rider_id": self.rider_id,
            "x": self.x,
            "y": self.y,
            "speed": self.speed,
            "state": self.state,
            "special_case": self.special_case,
            "orders": [order.id for order in self.orders],
        }
