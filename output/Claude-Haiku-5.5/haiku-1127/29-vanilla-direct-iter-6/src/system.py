"""System management: funds, rider recruitment, order dispatch and ticks."""

import logging
import math

from globalvar import _init, get_value, set_value
from order import OrderManager
from path_planner import PathPlanner
from order_model import STATUS_COMPLETED
from rider import IDLE, Rider

logger = logging.getLogger(__name__)

INITIAL_FUNDS = 1000
RECRUIT_THRESHOLD = 300
RECRUIT_COST = 300


def init_system() -> None:
    """Initialize all core parameters of the system.

    Sets funds to 1000, an empty rider list, rider ID counter to 0, the
    running flag to True, the tick counter to 0 and an empty order history.
    """
    _init()
    set_value("funds", INITIAL_FUNDS)
    set_value("riders", [])
    set_value("rider_id_counter", 0)
    set_value("running", True)
    set_value("tick", 0)
    set_value("orders", [])
    logger.info("System initialised with funds=%d", INITIAL_FUNDS)


class SystemManager:
    """Core coordinator for funds, riders, orders and simulated time."""

    def __init__(self) -> None:
        """Create the manager; expects ``init_system`` to have been called."""
        self.order_manager = OrderManager()
        self.planner = PathPlanner()

    @property
    def funds(self) -> int:
        """Current system fund balance (may be negative)."""
        return get_value("funds")

    @property
    def riders(self) -> list:
        """List of all riders."""
        return get_value("riders")

    @property
    def tick_count(self) -> int:
        """Current simulated tick."""
        return get_value("tick")

    @property
    def running(self) -> bool:
        """Whether the main loop should keep running."""
        return bool(get_value("running"))

    def shutdown(self) -> None:
        """Request the main loop to stop."""
        set_value("running", False)
        logger.info("System shutdown requested")

    def rider_by_id(self, rider_id: int):
        """Return the rider with the given ID, or None."""
        for rider in self.riders:
            if rider.rider_id == rider_id:
                return rider
        return None

    def idle_riders(self) -> list:
        """Return riders that are idle and hold no orders."""
        return [r for r in self.riders if r.state == IDLE and not r.orders]

    def create_rider(self) -> Rider:
        """Create a new rider, register it and deduct the recruitment cost.

        Returns:
            The newly created Rider.
        """
        rider_id = get_value("rider_id_counter") + 1
        set_value("rider_id_counter", rider_id)
        rider = Rider(rider_id)
        self.riders.append(rider)
        set_value("funds", self.funds - RECRUIT_COST)
        logger.info("Recruited rider %d (funds now %d)", rider_id, self.funds)
        return rider

    def try_recruit(self) -> list:
        """Recruit riders while funds allow and pending orders exceed idle riders.

        Returns:
            List of riders created by this call (possibly empty).
        """
        created = []
        while (
            self.funds >= RECRUIT_THRESHOLD
            and len(self.order_manager.pending_orders()) > len(self.idle_riders())
        ):
            created.append(self.create_rider())
        return created

    def _dispatch_pending(self) -> None:
        """Try to recruit and assign all pending orders in arrival order."""
        pending = self.order_manager.pending_orders()
        if not pending:
            return
        self.try_recruit()
        for order in pending:
            if self.order_manager.assign(order) is None:
                break

    def submit_order(self, restaurant_pos, customer_pos) -> dict:
        """Create an order, recruit if needed and assign it.

        Args:
            restaurant_pos: Restaurant (x, y) in range 0-800.
            customer_pos: Customer (x, y) in range 0-800.

        Returns:
            Dictionary with keys:
                "order": the created Order,
                "new_riders": list of riders recruited for this order,
                "rider": assigned Rider or None,
                "route": waypoint list from rider to restaurant to customer,
                "distance": total route length in units,
                "eta": estimated ticks to delivery (direct route estimate).

        Raises:
            ValueError: If the coordinates are invalid.
        """
        before = len(self.riders)
        order = self.order_manager.create_order(restaurant_pos, customer_pos)
        self._dispatch_pending()
        new_riders = list(self.riders[before:])
        rider = self.rider_by_id(order.rider_id) if order.rider_id is not None else None

        route = []
        distance = 0
        eta = None
        if rider is not None:
            first = self.planner.route(rider.position, order.res_pos)
            second = self.planner.route(order.res_pos, order.cus_pos)
            route = first + second[1:]
            distance = self.planner.route_length(route)
            eta = math.ceil(distance / rider.speed) if rider.speed > 0 else None
        return {
            "order": order,
            "new_riders": new_riders,
            "rider": rider,
            "route": route,
            "distance": distance,
            "eta": eta,
        }

    def _completed_count(self) -> int:
        """Return the number of completed orders in history."""
        return sum(1 for o in get_value("orders") or [] if o.status == STATUS_COMPLETED)

    def advance(self, ticks: int = 1) -> int:
        """Advance the simulation by a number of ticks.

        Each tick: increment the clock, dispatch pending orders and move every
        rider. Exceptions from a single rider are logged and do not stop the
        simulation (error recovery).

        Args:
            ticks: Number of ticks to simulate.

        Returns:
            Number of orders completed during these ticks.
        """
        completed_before = self._completed_count()
        for _ in range(max(0, int(ticks))):
            set_value("tick", self.tick_count + 1)
            self._dispatch_pending()
            for rider in list(self.riders):
                try:
                    rider.move()
                except Exception:  # error recovery: keep simulating
                    logger.exception("Rider %s failed to move", rider.rider_id)
                    rider.state = IDLE
        return self._completed_count() - completed_before

    def to_dict(self) -> dict:
        """Return a JSON-serializable snapshot of the system state."""
        return {
            "funds": self.funds,
            "tick": self.tick_count,
            "rider_id_counter": get_value("rider_id_counter"),
            "riders": [
                {
                    "rider_id": r.rider_id,
                    "x": r.x,
                    "y": r.y,
                    "speed": r.speed,
                    "state": r.state,
                    "special_case": r.special_case,
                    "order_ids": [o.id for o in r.orders],
                    "log": r.log,
                }
                for r in self.riders
            ],
            "orders": [
                {
                    "id": o.id,
                    "restaurant": list(o.res_pos),
                    "customer": list(o.cus_pos),
                    "status": o.status,
                    "rider_id": o.rider_id,
                    "start_tick": o.start_tick,
                    "pickup_tick": o.pickup_tick,
                    "completion_tick": o.completion_tick,
                    "distance": o.distance,
                    "time_taken": o.time_taken,
                }
                for o in get_value("orders") or []
            ],
        }
