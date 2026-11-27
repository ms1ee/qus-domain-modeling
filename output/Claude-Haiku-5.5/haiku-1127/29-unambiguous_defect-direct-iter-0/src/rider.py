"""Rider entity: state machine, street movement and event logging."""

import random

from globalvar import get_value, set_value
from path_planner import PathPlanner

STATE_IDLE = 0
STATE_PICKING_UP = 1
STATE_DELIVERING = 2
STATE_NAMES = {
    STATE_IDLE: "idle",
    STATE_PICKING_UP: "picking up",
    STATE_DELIVERING: "delivering",
}
SPEED_CHOICES = (80, 100, 120)


def _current_tick():
    """Return the global simulated time as an integer."""
    return get_value("tick", 0) or 0


class Rider:
    """A delivery rider who moves along streets and serves orders.

    Attributes:
        rider_id: Unique integer identifier.
        x: Current x coordinate.
        y: Current y coordinate.
        speed: Movement speed in units per tick.
        state: 0 idle, 1 picking up, 2 delivering.
        orders: Assigned orders (pending and in progress).
        special_case: True when moving straight towards a target directly
            above or below (or beside) the rider on the same street.
        current_order: The order currently being served, or None.
        distance_travelled: Total distance moved by this rider.
        log: List of dict entries with keys ``event``, ``order_id``, ``time``,
            ``rider_id``, ``x``, ``y`` and ``state``.
    """

    def __init__(self, rider_id):
        """Create a rider on a random street point with an idle status.

        Args:
            rider_id: Unique integer identifier for the rider.
        """
        self.rider_id = int(rider_id)
        self.x, self.y = random.choice(PathPlanner.all_centres())
        self.speed = random.choice(SPEED_CHOICES)
        self.state = STATE_IDLE
        self.orders = []
        self.special_case = False
        self.current_order = None
        self.distance_travelled = 0
        self.log = []
        self._record("spawn", None)

    @property
    def position(self):
        """Return the current position as an ``(x, y)`` tuple."""
        return (self.x, self.y)

    def _record(self, event, order_id):
        """Append a status-change entry to the rider log.

        Args:
            event: Event name such as ``accepted_order``.
            order_id: Related order ID, or None.
        """
        self.log.append({
            "event": event,
            "order_id": order_id,
            "time": _current_tick(),
            "rider_id": self.rider_id,
            "x": self.x,
            "y": self.y,
            "state": self.state,
        })

    def _next_pending_order(self):
        """Select the pending order whose restaurant is nearest.

        Returns:
            The nearest order in ``self.orders``.
        """
        return min(
            self.orders,
            key=lambda o: (PathPlanner.manhattan(self.position, o.res_pos), o.id),
        )

    def _travel_towards(self, target):
        """Move one tick towards ``target`` along the street grid.

        Args:
            target: Destination ``(x, y)`` tuple.
        """
        tx, ty = target
        nx, ny, moved = PathPlanner.step_towards(self.x, self.y, tx, ty, self.speed)
        self.x, self.y = nx, ny
        self.distance_travelled += moved
        if self.current_order is not None:
            self.current_order.travelled += moved
        self.special_case = self.x == tx and self.y != ty

    def _complete_current_order(self, now):
        """Finish the current order, release the rider and credit funds.

        Args:
            now: Current simulated tick.
        """
        order = self.current_order
        order.complete(now)
        if order in self.orders:
            self.orders.remove(order)
        self.current_order = None
        self.state = STATE_IDLE
        self.special_case = False
        self._record("delivered_to_customer", order.id)
        config = get_value("config") or {}
        fee = int(config.get("delivery_fee", 0))
        set_value("funds", (get_value("funds") or 0) + fee)

    def move(self):
        """Advance the rider by one tick, applying state transitions.

        Transitions:
            Idle -> Picking Up when an order is accepted.
            Picking Up -> Delivering on arrival at the restaurant.
            Delivering -> Idle on delivery to the customer.
        """
        now = _current_tick()
        if self.state == STATE_IDLE:
            if not self.orders:
                self.special_case = False
                return
            order = self._next_pending_order()
            self.current_order = order
            order.status = "picking_up"
            order.accepted_tick = now
            self.state = STATE_PICKING_UP
            self._record("accepted_order", order.id)

        if self.current_order is None:
            # Error recovery: an in-progress state without an order is reset.
            self.state = STATE_IDLE
            return

        if self.state == STATE_PICKING_UP:
            order = self.current_order
            self._travel_towards(order.res_pos)
            if self.position == order.res_pos:
                self.state = STATE_DELIVERING
                order.status = "delivering"
                order.pickup_tick = now
                self._record("arrived_at_merchant", order.id)
        elif self.state == STATE_DELIVERING:
            order = self.current_order
            self._travel_towards(order.cus_pos)
            if self.position == order.cus_pos:
                self._complete_current_order(now)

    def to_dict(self):
        """Serialise the rider to a JSON-compatible dictionary.

        Returns:
            Dictionary describing the rider and its log.
        """
        return {
            "rider_id": self.rider_id,
            "x": self.x,
            "y": self.y,
            "speed": self.speed,
            "state": self.state,
            "orders": [o.id for o in self.orders],
            "special_case": self.special_case,
            "distance_travelled": self.distance_travelled,
            "log": list(self.log),
        }
