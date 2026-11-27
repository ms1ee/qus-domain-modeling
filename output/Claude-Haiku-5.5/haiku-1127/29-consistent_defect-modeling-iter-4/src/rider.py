"""Rider model: state machine, movement along streets and event log.

Rider states:
    0 (idle): available for new orders.
    1 (picking up): travelling to the restaurant of the current order.
    2 (delivering): travelling to the customer of the current order.

Every state change is recorded in ``Rider.log`` as a dictionary with at
least the keys ``event`` and ``order_id``.
"""

import logging
from typing import Any, Dict, List, Optional

import globalvar
from order_model import (
    STATUS_ASSIGNED,
    STATUS_COMPLETED,
    Order,
)
from path_planner import PathPlanner

logger = logging.getLogger(__name__)

STATE_IDLE = 0
STATE_PICKING_UP = 1
STATE_DELIVERING = 2
STATE_NAMES = {
    STATE_IDLE: "idle",
    STATE_PICKING_UP: "picking up",
    STATE_DELIVERING: "delivering",
}

# The PRD lists both 10 and 20 units/tick; the rider data model fixes it at 20.
DEFAULT_RIDER_SPEED = 20
START_X = 400
START_Y = 400

EVENT_SPAWN = "spawn"
EVENT_ACCEPTED = "accepted_order"
EVENT_ARRIVED = "arrived_at_merchant"
EVENT_DELIVERED = "delivered_to_customer"


class Rider:
    """A delivery rider that moves on the street grid and serves orders.

    Attributes:
        rider_id (int): Unique identifier.
        x, y (int): Current position.
        speed (int): Units travelled per tick.
        state (int): 0 idle, 1 picking up, 2 delivering.
        orders (list[Order]): Assigned orders, including delivery history.
        special_case (bool): True while moving in a straight line toward a
            target directly above, below or beside the rider.
        log (list[dict]): Status change history.
        planner (PathPlanner): Pathfinding helper.
    """

    def __init__(self, rider_id: int, x: int = START_X, y: int = START_Y,
                 speed: int = DEFAULT_RIDER_SPEED) -> None:
        """Create a rider on a road point.

        Args:
            rider_id: Unique rider identifier.
            x: Initial x coordinate.
            y: Initial y coordinate.
            speed: Units per tick.
        """
        self.rider_id = rider_id
        self.x = x
        self.y = y
        self.speed = speed
        self.state = STATE_IDLE
        self.orders: List[Order] = []
        self.special_case = False
        self.log: List[Dict[str, Any]] = []
        self.planner = PathPlanner()
        self._record(EVENT_SPAWN, None)
        logger.info("Rider #%d spawned at (%d, %d)", rider_id, x, y)

    def _now(self) -> int:
        """Return the current simulated tick from the global store."""
        return int(globalvar.get_value("simulated_time", 0) or 0)

    def _record(self, event: str, order_id: Optional[int]) -> Dict[str, Any]:
        """Append a status change entry to the rider log.

        Args:
            event: Event name.
            order_id: Related order ID, or None.

        Returns:
            The created log entry.
        """
        entry = {
            "time": self._now(),
            "event": event,
            "order_id": order_id,
            "rider_id": self.rider_id,
            "x": self.x,
            "y": self.y,
            "state": self.state,
        }
        self.log.append(entry)
        logger.debug("Rider #%d event=%s order=%s", self.rider_id, event, order_id)
        return entry

    def position(self) -> tuple:
        """Return the current position as ``(x, y)``."""
        return self.x, self.y

    def active_orders(self) -> List[Order]:
        """Return orders that are not yet completed, in service order."""
        return [order for order in self.orders if order.status != STATUS_COMPLETED]

    def current_order(self) -> Optional[Order]:
        """Return the order currently being served, or None."""
        active = self.active_orders()
        return active[0] if active else None

    def refresh_state(self) -> None:
        """Acknowledge newly assigned orders and update idle/picking-up state.

        If the rider is idle and receives a new order it switches to the
        picking-up state and logs ``accepted_order``. This method is also
        called by the order manager right after an assignment.
        """
        order = self.current_order()
        if order is None:
            if self.state != STATE_IDLE:
                self.state = STATE_IDLE
            return
        if order.status == STATUS_ASSIGNED:
            order.mark_accepted()
            if self.state == STATE_IDLE:
                self.state = STATE_PICKING_UP
            self._record(EVENT_ACCEPTED, order.id)

    def move(self) -> None:
        """Advance the rider by one tick.

        Handles the state transitions:
            idle -> picking up when an order is accepted,
            picking up -> delivering on arrival at the restaurant,
            delivering -> picking up (next order) or idle on delivery.
        """
        self.refresh_state()
        order = self.current_order()
        if order is None:
            self.state = STATE_IDLE
            self.special_case = False
            return
        if self.state == STATE_IDLE:
            self.state = STATE_PICKING_UP

        if self.state == STATE_PICKING_UP:
            if self.position() == order.restaurant_pos:
                self._arrive_at_merchant(order)
                return
            target = order.restaurant_pos
        else:
            if self.position() == order.customer_pos:
                self._deliver(order)
                return
            target = order.customer_pos

        self.x, self.y, self.special_case = self.planner.next_step(
            self.x, self.y, target[0], target[1], self.speed
        )

    def _arrive_at_merchant(self, order: Order) -> None:
        """Handle arrival at the restaurant: pick up the food.

        Args:
            order: The order being picked up.
        """
        order.mark_picked_up(self._now())
        self.state = STATE_DELIVERING
        self.special_case = False
        self._record(EVENT_ARRIVED, order.id)

    def _deliver(self, order: Order) -> None:
        """Handle delivery to the customer and release the rider if free.

        Args:
            order: The order that has just been delivered.
        """
        order.mark_completed(self._now())
        self._record(EVENT_DELIVERED, order.id)
        self.special_case = False
        if self.active_orders():
            self.state = STATE_PICKING_UP
            self.refresh_state()
        else:
            self.state = STATE_IDLE
        logger.info("Order #%d delivered by rider #%d", order.id, self.rider_id)

    def to_dict(self) -> Dict[str, Any]:
        """Return a JSON-serialisable representation of the rider."""
        return {
            "rider_id": self.rider_id,
            "x": self.x,
            "y": self.y,
            "speed": self.speed,
            "state": self.state,
            "special_case": self.special_case,
            "order_ids": [order.id for order in self.orders],
            "log": self.log,
        }
