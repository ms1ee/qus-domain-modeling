"""System manager: funds, rider recruitment, simulation ticks and persistence."""

import json
import logging
import os
from typing import Any, Dict, List, Tuple

from config import SystemConfig
from globalvar import _init, get_value, set_value
from grid import GridMap
from order import OrderManager
from path_planner import PathNotFoundError, PathPlanner
from rider import Rider

logger = logging.getLogger(__name__)

Point = Tuple[int, int]
DEFAULT_STATE_PATH = "dispatch_state.json"


class SystemManager:
    """Facade over the global simulation state.

    All state lives in ``globalvar``; this class provides the operations that
    change funds, recruit riders, advance time and persist data.
    """

    def __init__(self) -> None:
        """Create the facade. State is read from the global store."""
        self._recruit_count = 0

    # ------------------------------------------------------------------
    # state accessors
    # ------------------------------------------------------------------
    @property
    def config(self) -> SystemConfig:
        """System configuration."""
        return get_value("config")

    @property
    def planner(self) -> PathPlanner:
        """Shared path planner."""
        return get_value("path_planner")

    @property
    def order_manager(self) -> OrderManager:
        """Shared order manager."""
        return get_value("order_manager")

    @property
    def funds(self) -> int:
        """Current system funds."""
        return int(get_value("funds", 0))

    @funds.setter
    def funds(self, value: int) -> None:
        set_value("funds", int(value))

    @property
    def riders(self) -> List[Rider]:
        """All active riders."""
        return get_value("riders")

    @property
    def rider_id_counter(self) -> int:
        """Last rider ID handed out."""
        return int(get_value("rider_id_counter", 0))

    @property
    def running(self) -> bool:
        """Main loop control flag."""
        return bool(get_value("running", True))

    @running.setter
    def running(self, value: bool) -> None:
        set_value("running", bool(value))

    @property
    def simulated_time(self) -> int:
        """Current simulated tick."""
        return int(get_value("simulated_time", 0))

    # ------------------------------------------------------------------
    # funds and recruitment
    # ------------------------------------------------------------------
    def add_funds(self, amount: int) -> None:
        """Add (or subtract, if negative) funds."""
        self.funds = self.funds + int(amount)

    def create_rider(self) -> Rider:
        """Create a new rider with a fresh unique ID and register it."""
        counter = self.rider_id_counter + 1
        set_value("rider_id_counter", counter)
        rider = Rider(counter)
        self.riders.append(rider)
        logger.info("Recruited rider %d", counter)
        return rider

    def recruit_riders(self) -> List[int]:
        """Recruit riders while funds are at or above the threshold.

        Each recruitment costs ``recruitment_cost`` from the funds.

        Returns:
            IDs of the riders created during this call.
        """
        new_ids: List[int] = []
        threshold = self.config.recruitment_threshold
        cost = self.config.recruitment_cost
        while self.funds >= threshold:
            rider = self.create_rider()
            self.funds = self.funds - cost
            new_ids.append(rider.rider_id)
        return new_ids

    # ------------------------------------------------------------------
    # orders and simulation
    # ------------------------------------------------------------------
    def place_order(self, restaurant_pos, customer_pos) -> Dict[str, Any]:
        """Create an order, collect its fee, recruit riders and assign it.

        Args:
            restaurant_pos: ``[x, y]`` restaurant location.
            customer_pos: ``[x, y]`` customer location.

        Returns:
            Dictionary with keys "order", "new_riders" (list of IDs),
            "rider" (Rider or None) and "route" (Route or None; preview of the
            assigned rider's restaurant-then-customer path).
        """
        order = self.order_manager.create_order(restaurant_pos, customer_pos)
        self.add_funds(self.config.order_fee)
        new_riders = self.recruit_riders()
        rider = self.order_manager.submit(order)
        route = None
        if rider is not None:
            try:
                route = self.planner.plan_multi(
                    rider.position,
                    [order.restaurant_pos, order.customer_pos],
                    rider.speed)
            except PathNotFoundError as exc:
                logger.error("Route preview failed: %s", exc)
        return {
            "order": order,
            "new_riders": new_riders,
            "rider": rider,
            "route": route,
        }

    def tick(self) -> None:
        """Advance the simulation by one tick.

        Increments the clock, retries pending orders, moves every rider and
        recruits riders if funds allow. An error in one rider is logged and
        that rider is reset, so the rest of the system keeps running.
        """
        set_value("simulated_time", self.simulated_time + 1)
        self.order_manager.retry_pending()
        for rider in list(self.riders):
            try:
                rider.move()
            except Exception:  # error recovery: keep the simulation alive
                logger.exception("Rider %d failed; resetting its state",
                                 rider.rider_id)
                rider.reset_after_error()
        self.recruit_riders()

    def status_snapshot(self) -> Dict[str, Any]:
        """Return a summary of the current state."""
        return {
            "simulated_time": self.simulated_time,
            "funds": self.funds,
            "rider_count": len(self.riders),
            "riders": [r.to_dict() for r in self.riders],
            "active_orders": len(self.order_manager.active_orders()),
            "pending_orders": len(self.order_manager.pending),
        }

    # ------------------------------------------------------------------
    # persistence
    # ------------------------------------------------------------------
    def save_state(self, path: str = DEFAULT_STATE_PATH) -> str:
        """Save configuration, riders and order history as JSON.

        Args:
            path: Destination file path.

        Returns:
            The path the data was written to.

        Raises:
            ValueError: If the file cannot be written.
        """
        data = {
            "config": self.config.to_dict(),
            "simulated_time": self.simulated_time,
            "funds": self.funds,
            "rider_id_counter": self.rider_id_counter,
            "riders": [r.to_dict() for r in self.riders],
            "orders": [o.to_dict() for o in self.order_manager.orders],
        }
        tmp_path = f"{path}.tmp"
        try:
            with open(tmp_path, "w", encoding="utf-8") as handle:
                json.dump(data, handle, indent=2)
            os.replace(tmp_path, path)
        except OSError as exc:
            logger.error("Could not save state to %s: %s", path, exc)
            raise ValueError(f"could not save state to '{path}': {exc}") from None
        logger.info("State saved to %s", path)
        return path


def init_system() -> None:
    """Initialise global variables, configuration and core managers.

    Sets the funds to the configured initial value, an empty rider list, the
    rider ID counter to 0, the running flag to True and the simulated time to 0.
    """
    _init()
    config = SystemConfig.load()
    grid = GridMap(config.map_size, config.cell_size)
    set_value("config", config)
    set_value("grid", grid)
    set_value("path_planner", PathPlanner(grid))
    set_value("order_manager", OrderManager())
    set_value("funds", config.initial_funds)
    set_value("riders", [])
    set_value("rider_id_counter", 0)
    set_value("running", True)
    set_value("simulated_time", 0)
    set_value("system_manager", SystemManager())
    logger.info("System initialised (funds=%d)", config.initial_funds)
