"""Core system manager: funds, rider recruitment, order flow and the clock."""

import logging
from typing import Any, Dict, List, Optional, Sequence

import globalvar
from order import OrderManager
from path_planner import PathPlanner
from rider import Rider

logger = logging.getLogger(__name__)


class SystemManager:
    """Coordinates riders, orders, funds and simulated time.

    State is kept in the global store (see ``globalvar``) so that every
    module observes the same values.
    """

    def __init__(self) -> None:
        """Create the manager using the currently stored global state."""
        self.order_manager = OrderManager()
        self.path_planner = PathPlanner()

    # ----- global state accessors -------------------------------------
    @property
    def funds(self) -> int:
        """Current system funds (may be negative)."""
        return int(globalvar.get_value("funds", 0))

    @funds.setter
    def funds(self, value: int) -> None:
        globalvar.set_value("funds", int(value))

    @property
    def rider_id_counter(self) -> int:
        """Last rider ID issued."""
        return int(globalvar.get_value("rider_id_counter", 0))

    @property
    def is_running(self) -> bool:
        """Whether the main loop should keep running."""
        return bool(globalvar.get_value("is_running", False))

    @is_running.setter
    def is_running(self, value: bool) -> None:
        globalvar.set_value("is_running", bool(value))

    @property
    def current_time(self) -> int:
        """Current simulated tick."""
        return int(globalvar.get_value("current_time", 0))

    @property
    def riders(self) -> List[Rider]:
        """The live rider list."""
        riders = globalvar.get_value("riders")
        if riders is None:
            riders = []
            globalvar.set_value("riders", riders)
        return riders

    # ----- rider management -------------------------------------------
    def find_rider(self, rider_id: int) -> Optional[Rider]:
        """Return the rider with ``rider_id`` or None."""
        for rider in self.riders:
            if rider.rider_id == rider_id:
                return rider
        return None

    def idle_rider_count(self) -> int:
        """Number of riders that are free to accept a new order."""
        return sum(1 for r in self.riders if r.is_idle())

    def pending_order_count(self) -> int:
        """Number of orders waiting for assignment."""
        return len(self.order_manager.pending_orders())

    def recruit_rider(self) -> Rider:
        """Create a new rider, deduct the recruitment cost and register it.

        Returns:
            The newly created Rider.
        """
        self.globalvar_counter_increment()
        rider = Rider(self.rider_id_counter)
        self.riders.append(rider)
        self.funds = self.funds - int(globalvar.get_value("recruit_cost", 500))
        logger.info("recruited rider %d, funds now %d", rider.rider_id, self.funds)
        return rider

    def globalvar_counter_increment(self) -> None:
        """Increment the global rider ID counter."""
        globalvar.set_value("rider_id_counter", self.rider_id_counter + 1)

    def maybe_recruit(self) -> int:
        """Recruit riders while funds allow and pending orders exceed idle riders.

        Returns:
            The number of riders recruited.
        """
        min_funds = int(globalvar.get_value("min_recruit_funds", 300))
        count = 0
        while self.funds >= min_funds and self.pending_order_count() > self.idle_rider_count():
            self.recruit_rider()
            count += 1
        return count

    # ----- order flow ---------------------------------------------------
    def submit_order(self, restaurant_pos: Sequence[int], customer_pos: Sequence[int]) -> Dict[str, Any]:
        """Create an order, recruit if needed and assign it.

        Args:
            restaurant_pos: Restaurant ``(x, y)``.
            customer_pos: Customer ``(x, y)``.

        Returns:
            Dictionary with keys ``order``, ``new_rider`` (bool), ``rider``
            (the assigned Rider or None) and ``recruited`` (count).
        """
        order = self.order_manager.create_order(restaurant_pos, customer_pos)
        recruited = self.maybe_recruit()
        self.order_manager.assign_pending_orders()
        rider = self.find_rider(order.rider_id) if order.rider_id is not None else None
        return {
            "order": order,
            "new_rider": recruited > 0,
            "rider": rider,
            "recruited": recruited,
        }

    # ----- simulation clock ---------------------------------------------
    def tick(self) -> None:
        """Advance the simulation by one unit of time.

        Every rider is moved once; errors in a single rider are logged and do
        not stop the rest of the system. Pending orders are then re-evaluated.
        """
        globalvar.set_value("current_time", self.current_time + 1)
        for rider in list(self.riders):
            try:
                rider.move()
            except Exception:  # error recovery: keep the simulation alive
                logger.exception("rider %s failed during tick", rider.rider_id)
        self.maybe_recruit()
        self.order_manager.assign_pending_orders()

    def run_ticks(self, count: int) -> None:
        """Advance the simulation by ``count`` ticks."""
        for _ in range(count):
            self.tick()

    def stop(self) -> None:
        """Request the main loop to terminate."""
        self.is_running = False


def init_system() -> SystemManager:
    """Initialise global state with default parameters and return the manager.

    Returns:
        A ready-to-use SystemManager.
    """
    globalvar._init()
    return SystemManager()
