"""Rider model: state machine, street-grid movement and event logging.

Rider states:
    0 (IDLE)        - available for new orders.
    1 (PICKING_UP)  - driving to the restaurant.
    2 (DELIVERING)  - driving to the customer.

An order is assigned by appending it to ``rider.orders``. Each call to
``move()`` advances the rider by one tick; state transitions and their log
entries happen inside ``move()``.
"""

import logging
import random

import globalvar
from grid import is_street_point, road_lattice_points
from path_planner import PathPlanner

logger = logging.getLogger("dispatch.rider")

IDLE = 0
PICKING_UP = 1
DELIVERING = 2
STATE_NAMES = {IDLE: "idle", PICKING_UP: "picking up", DELIVERING: "delivering"}
SPEED_CHOICES = (50, 100)

_planner = PathPlanner()


class Rider:
    """A delivery rider moving on the street grid.

    Attributes:
        rider_id (int): Unique identifier.
        x (int): Current x coordinate.
        y (int): Current y coordinate.
        speed (int): Movement budget in units per tick (multiple of 50).
        state (int): One of IDLE, PICKING_UP, DELIVERING.
        orders (list[Order]): Assigned orders; index 0 is the active order.
        special_case (bool): True while the rider is off-street (at a location).
        path (list[tuple]): Remaining waypoints of the current route.
        log (list[dict]): Event log entries with keys including "event"
            and "order_id".
    """

    def __init__(self, rider_id):
        """Create a rider on a random road point.

        Args:
            rider_id: Unique integer identifier.
        """
        self.rider_id = int(rider_id)
        self.x, self.y = random.choice(road_lattice_points())
        self.speed = SPEED_CHOICES[self.rider_id % len(SPEED_CHOICES)]
        self.state = IDLE
        self.orders = []
        self.special_case = False
        self.path = []
        self.log = []
        logger.info("rider #%d spawned at (%d, %d)", self.rider_id, self.x, self.y)
        self._record("spawn", None, f"spawned at ({self.x}, {self.y}) speed {self.speed}")

    def position(self):
        """Return the current position as an (x, y) tuple."""
        return (self.x, self.y)

    def _record(self, event, order_id, description=""):
        """Append an entry to the rider's event log.

        Args:
            event: Event name ("spawn", "accepted_order",
                "arrived_at_merchant", "delivered_to_customer").
            order_id: Related order id or None.
            description: Optional free-text detail.
        """
        self.log.append({
            "tick": globalvar.get_current_tick(),
            "event": event,
            "order_id": order_id,
            "rider_id": self.rider_id,
            "state": self.state,
            "x": self.x,
            "y": self.y,
            "description": description,
        })

    def _other_positions(self):
        """Return positions of all other riders (used for conflict avoidance)."""
        riders = globalvar.get_value("riders") or []
        return {r.position() for r in riders if r is not self}

    def _plan_to(self, target):
        """Plan a route from the current position to ``target``.

        Args:
            target: Destination (x, y) grid point.
        """
        route = _planner.plan(self.position(), target, self._other_positions())
        self.path = route[1:]

    def estimate_route(self, order):
        """Return the planned route: current position -> restaurant -> customer.

        Args:
            order: The Order to estimate.

        Returns:
            list[tuple]: Ordered waypoints including the starting position.
        """
        occupied = self._other_positions()
        to_restaurant = _planner.plan(self.position(), order.res_pos, occupied)
        to_customer = _planner.plan(order.res_pos, order.cus_pos, occupied)
        return to_restaurant + to_customer[1:]

    def _advance(self):
        """Consume this tick's movement budget along the planned path."""
        budget = self.speed
        while self.path and budget > 0:
            nx, ny = self.path[0]
            dist = abs(nx - self.x) + abs(ny - self.y)
            if dist > budget:
                break
            self.x, self.y = nx, ny
            budget -= dist
            self.path.pop(0)
        self.special_case = not is_street_point(self.x, self.y)

    def _start_pickup(self):
        """Accept the first order: switch to PICKING_UP and plan to the restaurant."""
        order = self.orders[0]
        self.state = PICKING_UP
        order.status = "picking_up"
        self._plan_to(order.res_pos)
        self._record("accepted_order", order.id, f"heading to restaurant {order.res_pos}")

    def _arrive_at_merchant(self, order):
        """Handle arrival at the restaurant: switch to DELIVERING."""
        self.state = DELIVERING
        order.status = "delivering"
        self._record("arrived_at_merchant", order.id, f"picked up at {order.res_pos}")
        self._plan_to(order.cus_pos)

    def _deliver(self, order):
        """Handle delivery completion: release the order and become idle."""
        order.complete(globalvar.get_current_tick())
        self._record("delivered_to_customer", order.id,
                     f"delivered at {order.cus_pos} in {order.time_taken} tick(s)")
        self.orders.pop(0)
        self.state = IDLE
        self.path = []
        if self.orders:
            self._start_pickup()

    def move(self):
        """Advance the rider by one tick.

        Handles idle -> picking up (order accepted), picking up -> delivering
        (arrival at restaurant) and delivering -> idle (delivery complete).
        Re-plans automatically if the path was lost (error recovery).
        """
        if self.state == IDLE:
            if not self.orders:
                return
            self._start_pickup()
        self._advance()
        if self.path or not self.orders:
            return
        order = self.orders[0]
        here = self.position()
        if self.state == PICKING_UP:
            if here == order.res_pos:
                self._arrive_at_merchant(order)
            else:
                self._plan_to(order.res_pos)
        elif self.state == DELIVERING:
            if here == order.cus_pos:
                self._deliver(order)
            else:
                self._plan_to(order.cus_pos)

    def repair(self):
        """Fix inconsistent state fields.

        Returns:
            list[str]: Descriptions of every problem found and repaired.
        """
        problems = []
        if self.state not in STATE_NAMES:
            problems.append(f"invalid state {self.state!r} reset to idle")
            self.state = IDLE
            self.path = []
        if self.state != IDLE and not self.orders:
            problems.append("busy without orders reset to idle")
            self.state = IDLE
            self.path = []
        return problems

    def to_dict(self):
        """Return a JSON-serialisable representation of the rider."""
        return {
            "rider_id": self.rider_id,
            "x": self.x,
            "y": self.y,
            "speed": self.speed,
            "state": self.state,
            "special_case": self.special_case,
            "order_ids": [order.id for order in self.orders],
        }
