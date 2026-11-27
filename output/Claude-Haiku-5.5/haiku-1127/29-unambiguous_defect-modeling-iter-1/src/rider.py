"""Rider model: state machine, movement and event logging.

Rider states: 0 idle, 1 picking up (heading to restaurant),
2 delivering (heading to customer).
"""

import logging

import config
import globalvar
import grid_map
from path_planner import PathPlanner

logger = logging.getLogger(__name__)

IDLE = 0
PICKING_UP = 1
DELIVERING = 2
STATE_NAMES = {IDLE: "idle", PICKING_UP: "picking up", DELIVERING: "delivering"}

_planner = PathPlanner()
_SPAWN_POINTS = grid_map.all_intersections()


class Rider:
    """A delivery rider that serves a queue of orders."""

    def __init__(self, rider_id):
        """Create a rider on a street intersection.

        Args:
            rider_id: Unique integer identifier.
        """
        self.rider_id = int(rider_id)
        self.x, self.y = _SPAWN_POINTS[(self.rider_id * 13) % len(_SPAWN_POINTS)]
        self.speed = config.SETTINGS["base_rider_speed"] + 10 * (self.rider_id % 3)
        self.state = IDLE
        self.orders = []
        self.special_case = False
        self.log = []
        self._record("spawn", None)

    @property
    def position(self):
        """Current (x, y) position."""
        return (self.x, self.y)

    @property
    def state_name(self):
        """Human-readable state name."""
        return STATE_NAMES.get(self.state, "unknown")

    @staticmethod
    def _current_tick():
        """Return the current simulated tick."""
        return int(globalvar.get_value("current_tick") or 0)

    def _record(self, event, order_id):
        """Append a status-change entry to the rider log.

        Args:
            event: Event name (spawn, accepted_order, arrived_at_merchant,
                delivered_to_customer).
            order_id: Related order ID, or None.
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
        logger.info(
            "tick=%s rider=%s event=%s order=%s pos=(%s,%s) state=%s",
            entry["tick"], self.rider_id, event, order_id, self.x, self.y,
            self.state_name,
        )

    def target(self):
        """Return the current destination, or None if the rider has no orders."""
        if not self.orders:
            return None
        order = self.orders[0]
        if self.state == DELIVERING:
            return order.cus_pos
        return order.res_pos

    def _activate(self, order):
        """Start working on an order (idle -> picking up, or next order)."""
        if order.picked_up:
            self.state = DELIVERING
            order.set_status("delivering")
        else:
            self.state = PICKING_UP
            order.set_status("picking_up")
        self._record("accepted_order", order.order_id)

    def _arrive(self, order):
        """Handle arrival at the current destination."""
        if self.state == PICKING_UP:
            self.state = DELIVERING
            order.picked_up = True
            order.set_status("delivering")
            self._record("arrived_at_merchant", order.order_id)
        elif self.state == DELIVERING:
            self._deliver(order)

    def _deliver(self, order):
        """Complete the active order, pay the fee and release the rider."""
        self._record("delivered_to_customer", order.order_id)
        order.complete(self._current_tick())
        funds = int(globalvar.get_value("funds") or 0)
        globalvar.set_value("funds", funds + config.SETTINGS["delivery_fee"])
        self.orders.remove(order)
        if self.orders:
            self._activate(self.orders[0])
        else:
            self.state = IDLE
            self.special_case = False

    def _is_blocked(self, nx, ny):
        """Return True if a higher-priority rider occupies the next cell.

        Lower IDs always have priority, so the lowest-ID rider on any shared
        cell never waits and deadlocks are impossible.
        """
        riders = globalvar.get_value("riders") or []
        for other in riders:
            if other is self:
                continue
            if (
                other.rider_id < self.rider_id
                and other.state != IDLE
                and other.position == (nx, ny)
            ):
                return True
        return False

    def move(self):
        """Advance the rider by one tick.

        Performs the state transitions: idle -> picking up when an order is
        accepted, picking up -> delivering on arrival at the restaurant, and
        delivering -> idle (or next order) on delivery.
        """
        if not self.orders:
            if self.state != IDLE:
                self.state = IDLE
                self.special_case = False
            return
        order = self.orders[0]
        if self.state == IDLE:
            self._activate(order)
        target = self.target()
        if target is None:
            return
        if self.position == target:
            self._arrive(order)
            return
        tx, ty = target
        self.special_case = self.x == tx or self.y == ty
        nx, ny = _planner.step_toward(self.x, self.y, tx, ty, self.speed)
        if self._is_blocked(nx, ny):
            self.special_case = True
            logger.debug("rider %s yields at %s", self.rider_id, (nx, ny))
            return
        self.x, self.y = nx, ny
        if self.position == target:
            self._arrive(order)

    def __repr__(self):
        return (
            f"Rider(id={self.rider_id}, pos=({self.x},{self.y}), "
            f"state={self.state_name}, orders={len(self.orders)})"
        )
