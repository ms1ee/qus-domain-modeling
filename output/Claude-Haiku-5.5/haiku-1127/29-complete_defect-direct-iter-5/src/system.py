"""System lifecycle, funds, rider recruitment and the simulation tick."""

import logging
import math
from typing import Any, Dict, List, Optional, Sequence

import globalvar
from config import DEFAULT_PARAMS
from order import OrderManager
from pathplanner import PathPlanner, route_length
from rider import IDLE, Rider

logger = logging.getLogger(__name__)


class SystemManager:
    """Manages funds, riders, orders and the simulated clock."""

    def __init__(self) -> None:
        """Create the system manager and its order manager."""
        self.order_manager = OrderManager()
        self.planner = PathPlanner()

    # ------------------------------------------------------------ accessors
    def param(self, name: str) -> int:
        """Return a system parameter.

        Args:
            name: Parameter name.

        Returns:
            Parameter value.
        """
        params = globalvar.get_value("params", {}) or {}
        return params.get(name, DEFAULT_PARAMS[name])

    @property
    def funds(self) -> int:
        """Return the current system funds."""
        return globalvar.get_value("funds", 0)

    def add_funds(self, amount: int) -> None:
        """Add a (possibly negative) integer amount to the funds.

        Args:
            amount: Amount to add.
        """
        globalvar.set_value("funds", self.funds + int(amount))

    @property
    def tick_count(self) -> int:
        """Return the current simulated tick."""
        return globalvar.get_value("tick", 0)

    @property
    def riders(self) -> List[Rider]:
        """Return the live rider list."""
        return globalvar.get_value("riders")

    @property
    def orders(self) -> List[Any]:
        """Return the order history."""
        return globalvar.get_value("orders")

    def active_orders(self) -> List[Any]:
        """Return orders that are not yet completed."""
        return [o for o in self.orders if o.status != "completed"]

    # ------------------------------------------------------------- riders
    def next_rider_id(self) -> int:
        """Increment and return the rider ID counter."""
        counter = globalvar.get_value("rider_id_counter", 0) + 1
        globalvar.set_value("rider_id_counter", counter)
        return counter

    def create_rider(self) -> Rider:
        """Create a new idle rider at the spawn point and add it to the list.

        Returns:
            The new Rider.
        """
        rider = Rider(self.next_rider_id(), speed=self.param("default_speed"))
        self.riders.append(rider)
        logger.info("Recruited rider %s", rider.rider_id)
        return rider

    def get_rider(self, rider_id: int) -> Optional[Rider]:
        """Return the rider with the given ID, or None."""
        for rider in self.riders:
            if rider.rider_id == rider_id:
                return rider
        return None

    def remove_rider(self, rider_id: int) -> bool:
        """Remove an idle rider with no assigned orders.

        Args:
            rider_id: Identifier of the rider to remove.

        Returns:
            True if the rider was removed.
        """
        rider = self.get_rider(rider_id)
        if rider is None or rider.orders:
            return False
        self.riders.remove(rider)
        logger.info("Removed rider %s", rider_id)
        return True

    def check_recruitment(self) -> List[Rider]:
        """Recruit riders while funds are at or above the threshold.

        Each recruitment spends the recruit cost.

        Returns:
            List of newly created riders (empty if none).
        """
        created: List[Rider] = []
        threshold = self.param("recruit_threshold")
        cost = self.param("recruit_cost")
        while self.funds >= threshold:
            self.add_funds(-cost)
            created.append(self.create_rider())
        return created

    # ------------------------------------------------------------- orders
    def submit_order(self, coords: Sequence[object]) -> Dict[str, Any]:
        """Create, recruit for and assign a new order.

        Args:
            coords: ``[restaurant_x, restaurant_y, customer_x, customer_y]``.

        Returns:
            Dictionary with keys ``order``, ``new_riders``, ``rider``,
            ``route`` (planned route points), ``distance`` and ``eta_ticks``.

        Raises:
            ValueError: If the coordinates are invalid.
        """
        order = self.order_manager.create_order(coords)
        new_riders = self.check_recruitment()
        rider = self.order_manager.assign_order(order)
        route: List[Any] = []
        distance = 0
        eta = None
        if rider is not None:
            stops = [
                (order.res_center[0], order.res_center[1], "merchant"),
                (order.cus_center[0], order.cus_center[1], "customer"),
            ]
            route = self.planner.plan_route(rider.position(), stops)
            distance = route_length(route)
            eta = -(-distance // rider.speed)
        return {
            "order": order,
            "new_riders": new_riders,
            "rider": rider,
            "route": route,
            "distance": distance,
            "eta_ticks": eta,
        }

    # --------------------------------------------------------------- tick
    def tick(self) -> None:
        """Advance the simulation by one tick.

        Order of work: advance the clock, recruit riders if funds allow,
        assign pending orders, then move every rider.
        """
        globalvar.set_value("tick", self.tick_count + 1)
        self.check_recruitment()
        self.order_manager.process_pending()
        for rider in list(self.riders):
            rider.move()
        if self.funds < 0:
            logger.warning("System funds are negative: %s", self.funds)

    # ----------------------------------------------------- consistency
    def verify_consistency(self) -> List[str]:
        """Check and automatically repair the state of riders.

        Returns:
            List of human-readable problems that were found and repaired.
        """
        problems: List[str] = []
        seen_ids = set()
        for rider in self.riders:
            if rider.rider_id in seen_ids:
                problems.append(f"duplicate rider id {rider.rider_id}")
            seen_ids.add(rider.rider_id)
            if not rider.orders and (rider.state != IDLE or rider.route):
                problems.append(f"rider {rider.rider_id} had stale state; reset to idle")
                rider.reset_to_idle()
            if rider.current_order is not None and rider.current_order not in rider.orders:
                problems.append(f"rider {rider.rider_id} referenced a missing order; reset")
                rider.reset_to_idle()
        for message in problems:
            logger.warning(message)
        return problems

    # ------------------------------------------------------------ state
    def snapshot(self) -> Dict[str, Any]:
        """Return a JSON-serialisable snapshot of the whole system.

        Returns:
            Dictionary with parameters, funds, tick, riders and order history.
        """
        return {
            "tick": self.tick_count,
            "funds": self.funds,
            "parameters": dict(globalvar.get_value("params", {}) or {}),
            "riders": [rider.to_dict() for rider in self.riders],
            "orders": [order.to_dict() for order in self.orders],
        }

    def shutdown(self) -> None:
        """Signal the main loop to stop."""
        globalvar.set_value("running", False)
        logger.info("System shutdown requested")


def init_system(params: Optional[Dict[str, Any]] = None) -> SystemManager:
    """Initialise global state and return a ready SystemManager.

    Args:
        params: Optional parameter overrides (merged over the defaults).

    Returns:
        A SystemManager instance with empty rider list, counter 0, the
        running flag set to True and funds set to the initial funds.
    """
    globalvar._init()
    merged = dict(DEFAULT_PARAMS)
    if params:
        for key, value in params.items():
            if key in merged:
                merged[key] = value
    globalvar.set_value("params", merged)
    globalvar.set_value("funds", merged["initial_funds"])
    globalvar.set_value("running", True)
    logger.info("System initialised with funds=%s", merged["initial_funds"])
    return SystemManager()
