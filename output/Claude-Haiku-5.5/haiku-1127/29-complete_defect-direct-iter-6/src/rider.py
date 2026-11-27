"""Rider model: state machine, street-based movement and event log.

Rider states:
    0 - idle (available for new orders)
    1 - picking up (en route to the restaurant)
    2 - delivering (en route to the customer)

Transitions:
    idle -> picking up     when an assigned order is accepted (log "accepted_order")
    picking up -> delivering on arrival at merchant (log "arrived_at_merchant")
    delivering -> idle     on delivery to customer (log "delivered_to_customer")
"""

import logging

import globalvar
from geometry import is_cell_center, manhattan
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

SPAWN_POSITION = (50, 50)
MAX_WAIT_TICKS = 3


class Rider:
    """A delivery rider that moves along the street grid.

    Attributes:
        rider_id: Unique identifier.
        x, y: Current position in map units.
        speed: Movement speed in units per tick.
        state: Current state (0, 1 or 2).
        orders: Assigned orders; index 0 is the active order when not idle.
        special_case: True while the rider is waiting on a blocked street cell.
        log: List of event dicts with keys "tick", "event", "order_id", "x",
            "y", "state" and "rider_id".
        route: Remaining waypoints (cell centers) to visit.
        distance_travelled: Total distance moved by this rider.
    """

    def __init__(self, rider_id):
        """Create a rider at the spawn position in the idle state.

        Args:
            rider_id: Unique rider identifier.
        """
        self.rider_id = rider_id
        self.x, self.y = SPAWN_POSITION
        self.speed = int(globalvar.get_value("default_speed", 50))
        self.state = STATE_IDLE
        self.orders = []
        self.special_case = False
        self.log = []
        self.route = []
        self.distance_travelled = 0
        self.wait_ticks = 0
        self._stops = []
        self._planner = PathPlanner()
        self._record("spawn", None)

    @property
    def position(self):
        """Return the current ``(x, y)`` position."""
        return (self.x, self.y)

    @property
    def state_name(self):
        """Return a human-readable name for the current state."""
        return STATE_NAMES.get(self.state, "unknown")

    def move(self):
        """Advance the rider by one tick.

        Starts the next assigned order when idle, moves along the planned
        route by ``speed`` units, waits briefly at occupied street cells, and
        processes pickup/delivery events on arrival.
        """
        self._start_next_order()
        if self.state == STATE_IDLE:
            self.special_case = False
            return

        budget = self.speed
        while budget > 0 and self.route and self.state != STATE_IDLE:
            target = self.route[0]
            riders = self._riders()
            if is_cell_center(self.x, self.y) and PathPlanner.is_blocked(target, self, riders):
                if self.wait_ticks < MAX_WAIT_TICKS:
                    self.wait_ticks += 1
                    self.special_case = True
                    return
                logger.info(
                    "rider %s passes a blocked cell after waiting %s ticks",
                    self.rider_id,
                    self.wait_ticks,
                )
            self.wait_ticks = 0
            self.special_case = False

            gap = manhattan(self.position, target)
            if gap <= budget:
                self.x, self.y = target
                self.route.pop(0)
                self.distance_travelled += gap
                self._credit(gap)
                budget -= gap
                self._on_cell_reached()
            else:
                self._advance(budget)
                budget = 0

    def recover(self):
        """Reset the rider after an unexpected error so the simulation can continue.

        Active orders are returned to the "assigned" status so they will be
        restarted from the rider's current position.
        """
        logger.warning("recovering rider %s after an internal error", self.rider_id)
        for order in self.orders:
            if order.status in ("picking_up", "delivering"):
                order.status = "assigned"
        self.state = STATE_IDLE
        self.route = []
        self._stops = []
        self.special_case = False
        self.wait_ticks = 0

    def _riders(self):
        """Return the global list of riders."""
        return globalvar.get_value("riders", [])

    def _tick(self):
        """Return the current simulated time."""
        return globalvar.get_value("tick", 0)

    def _record(self, event, order_id):
        """Append an event entry to the rider log."""
        self.log.append(
            {
                "tick": self._tick(),
                "event": event,
                "order_id": order_id,
                "rider_id": self.rider_id,
                "x": self.x,
                "y": self.y,
                "state": self.state,
            }
        )

    def _current_order(self):
        """Return the order being served, or None when idle."""
        if self.state != STATE_IDLE and self.orders:
            return self.orders[0]
        return None

    def _credit(self, distance):
        """Add travelled distance to the active order."""
        order = self._current_order()
        if order is not None:
            order.distance += distance

    def _advance(self, budget):
        """Move partially toward the next waypoint by at most ``budget`` units."""
        tx, ty = self.route[0]
        remaining = budget
        dx = tx - self.x
        step = min(abs(dx), remaining)
        if dx:
            self.x += step if dx > 0 else -step
        remaining -= step
        dy = ty - self.y
        step = min(abs(dy), remaining)
        if dy:
            self.y += step if dy > 0 else -step
        remaining -= step
        moved = budget - remaining
        self.distance_travelled += moved
        self._credit(moved)

    def _start_next_order(self):
        """Transition idle -> picking up when an assigned order is waiting."""
        if self.state != STATE_IDLE or not self.orders:
            return
        order = self.orders[0]
        if order.status != "assigned":
            return
        order.status = "picking_up"
        order.picked_tick = None
        self.state = STATE_PICKING_UP
        self.special_case = False
        self.wait_ticks = 0
        order.trail.append(self.position)
        self._record("accepted_order", order.id)
        self._stops = [
            {"kind": "merchant", "point": order.res_center},
            {"kind": "customer", "point": order.cus_center},
        ]
        self.route = self._planner.plan_route(
            self.position,
            [order.res_center, order.cus_center],
            occupied=PathPlanner.occupied_cells(self._riders(), self),
        )
        self._process_stops()

    def _on_cell_reached(self):
        """Record the visited cell and process any stop at this position."""
        order = self._current_order()
        if order is not None:
            order.trail.append(self.position)
        self._process_stops()

    def _process_stops(self):
        """Handle merchant/customer arrivals when the rider stands on a stop."""
        while self._stops and self.position == self._stops[0]["point"]:
            stop = self._stops.pop(0)
            if stop["kind"] == "merchant":
                self._arrive_at_merchant()
            else:
                self._deliver_to_customer()

    def _arrive_at_merchant(self):
        """Transition picking up -> delivering on arrival at the restaurant."""
        order = self.orders[0]
        order.status = "delivering"
        order.picked_tick = self._tick()
        self.state = STATE_DELIVERING
        self._record("arrived_at_merchant", order.id)

    def _deliver_to_customer(self):
        """Transition delivering -> idle, complete the order and collect the fee."""
        order = self.orders.pop(0)
        order.complete(self._tick())
        fee = int(globalvar.get_value("delivery_fee", 0))
        globalvar.set_value("funds", int(globalvar.get_value("funds", 0)) + fee)
        self._record("delivered_to_customer", order.id)
        self.state = STATE_IDLE
        self.route = []
        self._stops = []
        self.special_case = False
