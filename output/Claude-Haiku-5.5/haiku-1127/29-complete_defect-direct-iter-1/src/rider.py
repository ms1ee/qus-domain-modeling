"""Rider model: state machine, street movement and event logging."""

import logging

import config
import globalvar
from path_planner import PathPlanner

logger = logging.getLogger(__name__)


class Rider:
    """A delivery rider that moves along the streets and serves orders.

    Attributes:
        rider_id: Unique integer identifier.
        x, y: Current position (cell-center coordinates).
        speed: Movement speed in units per tick.
        state: 0 = idle, 1 = picking up, 2 = delivering.
        orders: Assigned orders; ``orders[0]`` is the active order.
        special_case: True while on a direct straight-line leg.
        path: Remaining waypoints of the current leg.
        target: Current destination (restaurant or customer).
        log: Event entries with keys "event", "order_id", "tick", "x", "y",
            "state" and "rider_id".
    """

    def __init__(self, rider_id, speed=None):
        """Create a rider at the spawn point in the idle state.

        Args:
            rider_id: Unique integer identifier.
            speed: Optional speed in units per tick (default from config).

        Raises:
            TypeError: If rider_id is not an integer.
            ValueError: If speed is not positive.
        """
        if not isinstance(rider_id, int) or isinstance(rider_id, bool):
            raise TypeError("rider_id must be an integer")
        self.rider_id = rider_id
        self.x, self.y = config.SPAWN_POINT
        self.speed = int(speed) if speed is not None else config.DEFAULT_SPEED
        if self.speed <= 0:
            raise ValueError("speed must be a positive integer")
        self.state = config.STATE_IDLE
        self.orders = []
        self.special_case = False
        self.path = []
        self.target = None
        self.wait_ticks = 0
        self.log = []
        self._record("spawn", None)

    @property
    def position(self):
        """Return the current position as an (x, y) tuple."""
        return (self.x, self.y)

    def state_name(self):
        """Return the human-readable name of the current state."""
        return config.STATE_NAMES.get(self.state, "unknown")

    def move(self):
        """Advance the rider by one tick.

        Handles the idle → picking up transition when an order is assigned,
        moves along the planned route, and performs arrival transitions
        (picking up → delivering at the restaurant, delivering → idle at the
        customer). Every status change is written to ``self.log``.
        """
        if not self.orders:
            if self.state != config.STATE_IDLE:
                logger.warning("Rider %s had no orders; resetting to idle.",
                               self.rider_id)
                self.state = config.STATE_IDLE
                self.path = []
                self.target = None
            return

        if self.state == config.STATE_IDLE:
            self._accept_order(self.orders[0])

        if self.path:
            self._advance(self.speed)

        if not self.path and self.state != config.STATE_IDLE:
            self._on_arrival()

    def to_dict(self):
        """Return a JSON-serialisable representation of the rider."""
        return {
            "rider_id": self.rider_id,
            "x": self.x,
            "y": self.y,
            "speed": self.speed,
            "state": self.state,
            "orders": [order.id for order in self.orders],
            "special_case": self.special_case,
        }

    def __repr__(self):
        return (f"Rider(id={self.rider_id}, pos=({self.x},{self.y}), "
                f"state={self.state_name()}, orders={len(self.orders)})")

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------
    def _now(self):
        """Return the current simulated tick."""
        return globalvar.get_value("tick", 0)

    def _record(self, event, order_id):
        """Append a status-change entry to the rider log."""
        self.log.append({
            "event": event,
            "order_id": order_id,
            "tick": self._now(),
            "x": self.x,
            "y": self.y,
            "state": self.state,
            "rider_id": self.rider_id,
        })
        logger.info("Rider %s: %s (order %s) at (%s,%s)",
                    self.rider_id, event, order_id, self.x, self.y)

    def _other_positions(self):
        """Return the set of positions currently occupied by other riders."""
        riders = globalvar.get_value("riders", []) or []
        return {rider.position for rider in riders if rider is not self}

    def _append_route(self, order):
        """Record the current position in the active order's route."""
        if not order.route or order.route[-1] != self.position:
            order.route.append(self.position)

    def _plan_leg(self, target):
        """Plan the path for a new leg and update leg bookkeeping."""
        self.target = target
        self.path = PathPlanner.plan(self.position, target,
                                     self._other_positions())
        self.special_case = PathPlanner.is_straight(self.position, target)

    def _accept_order(self, order):
        """Start working on an order: idle → picking up."""
        self.state = config.STATE_PICKING_UP
        order.mark_picking_up()
        self._append_route(order)
        self._plan_leg(order.res_grid)
        self._record("accepted_order", order.id)

    def _advance(self, budget):
        """Move along the planned path using at most ``budget`` units.

        If the next waypoint is occupied by another rider, the rider waits up
        to ``WAIT_LIMIT`` ticks (deadlock/conflict avoidance) and then proceeds.
        """
        while budget > 0 and self.path:
            target_x, target_y = self.path[0]
            if (target_x, target_y) == self.position:
                self.path.pop(0)
                continue
            if (target_x, target_y) in self._other_positions():
                if self.wait_ticks < config.WAIT_LIMIT:
                    self.wait_ticks += 1
                    return
            self.wait_ticks = 0

            if target_x != self.x:
                distance = abs(target_x - self.x)
                step = min(budget, distance)
                self.x += step if target_x > self.x else -step
            else:
                distance = abs(target_y - self.y)
                step = min(budget, distance)
                self.y += step if target_y > self.y else -step
            budget -= step

            if self.position == (target_x, target_y):
                self.path.pop(0)
            if self.orders:
                self._append_route(self.orders[0])

    def _on_arrival(self):
        """Handle arrival at the current leg destination."""
        order = self.orders[0]
        if self.state == config.STATE_PICKING_UP:
            self.state = config.STATE_DELIVERING
            order.mark_delivering()
            self._plan_leg(order.cus_grid)
            self._record("arrived_at_merchant", order.id)
        elif self.state == config.STATE_DELIVERING:
            order.complete(self._now(), self.rider_id)
            globalvar.set_value("funds",
                                globalvar.get_value("funds", 0) + config.ORDER_FEE)
            completed = globalvar.get_value("completed_orders")
            if completed is not None:
                completed.append(order)
            self.orders.pop(0)
            self.state = config.STATE_IDLE
            self.path = []
            self.target = None
            self.special_case = False
            self._record("delivered_to_customer", order.id)
