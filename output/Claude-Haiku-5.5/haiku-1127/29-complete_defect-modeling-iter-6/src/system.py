"""System manager: funds, rider recruitment, simulation clock and persistence.

Every call to ``SystemManager.tick()`` is one unit of simulated time. Within a
tick the system first assigns pending orders, then moves every rider, credits
the delivery fee for completed orders and finally checks the recruitment
trigger.
"""

import json
import logging
from typing import Any, Dict, Optional, Tuple

import globalvar
from config import DEFAULT_CONFIG
from order import OrderManager
from order_model import Order
from path_planner import PathPlanner
from rider import Rider

logger = logging.getLogger(__name__)

SPAWN_POINT: Tuple[int, int] = (400, 400)  # a street intersection at map centre


class SystemManager:
    """Core manager for funds, riders, orders and the simulation clock.

    Attributes:
        config: Active system parameters.
        funds: System fund balance (integer, may be negative).
        rider_id_counter: Last rider id issued (ids start at 1).
        is_running: Main-loop control flag.
        current_tick: Simulated time.
        planner: Shared path planner.
        order_manager: The OrderManager owned by the system.
    """

    def __init__(self, config: Optional[Dict[str, Any]] = None) -> None:
        """Create the system manager with the given parameters.

        Args:
            config: Parameter overrides; missing keys use defaults.
        """
        self.config: Dict[str, Any] = dict(DEFAULT_CONFIG)
        if config:
            self.config.update(config)
        self.funds = int(self.config["initial_funds"])
        self.rider_id_counter = 0
        self.is_running = True
        self.current_tick = 0
        self.planner = PathPlanner()
        self.order_manager = OrderManager(
            load_penalty=int(self.config["load_penalty"]))
        globalvar.set_value("riders", [])
        globalvar.set_value("current_tick", 0)

    @property
    def riders(self) -> list:
        """The dynamic list of riders stored in the global variables."""
        riders = globalvar.get_value("riders")
        if riders is None:
            riders = []
            globalvar.set_value("riders", riders)
        return riders

    def create_rider(self) -> Rider:
        """Create a new idle rider at the spawn point and register it.

        Returns:
            The new Rider.
        """
        self.rider_id_counter += 1
        rider = Rider(self.rider_id_counter, x=SPAWN_POINT[0],
                      y=SPAWN_POINT[1],
                      speed=int(self.config["default_rider_speed"]),
                      planner=self.planner)
        self.riders.append(rider)
        logger.info("Recruited rider %d", rider.rider_id)
        return rider

    def recruit_rider_if_funded(self) -> Optional[Rider]:
        """Recruit a rider when funds reach the recruitment threshold.

        The recruitment cost is deducted from the funds.

        Returns:
            The new Rider, or None if funds are below the threshold.
        """
        if self.funds >= int(self.config["recruit_threshold"]):
            self.funds -= int(self.config["recruit_cost"])
            return self.create_rider()
        return None

    def submit_order(self, res_pos, cus_pos
                     ) -> Tuple[Order, Optional[Rider], Optional[Rider]]:
        """Create an order, assign it and run the simulation until delivery.

        Args:
            res_pos: Restaurant (x, y), 0-800.
            cus_pos: Customer (x, y), 0-800.

        Returns:
            Tuple ``(order, new_rider, assigned_rider)``. ``new_rider`` is
            the rider recruited for this order (or None). ``assigned_rider``
            is the rider chosen for the order (or None if still pending).

        Raises:
            ValueError: If a coordinate is invalid.
        """
        new_rider = self.recruit_rider_if_funded()
        order = self.order_manager.create_order(res_pos, cus_pos,
                                                self.current_tick)
        assigned = self.order_manager.assign_order(order)
        self.run_until_completed(order)
        return order, new_rider, assigned

    def tick(self) -> None:
        """Advance the simulation by one unit of time.

        Raises:
            RuntimeError: If the system has been shut down.
        """
        if not self.is_running:
            raise RuntimeError("System is not running")
        self.current_tick += 1
        globalvar.set_value("current_tick", self.current_tick)
        self.order_manager.try_assign_pending()
        for rider in list(self.riders):
            for order in rider.move():
                self._on_order_completed(order)
        self.recruit_rider_if_funded()

    def _on_order_completed(self, order: Order) -> None:
        """Release resources and credit the delivery fee for an order."""
        self.funds += int(self.config["delivery_fee"])
        logger.info("Order %d completed; funds now %d", order.id, self.funds)

    def run_ticks(self, count: int) -> None:
        """Advance the simulation by ``count`` ticks."""
        for _ in range(int(count)):
            self.tick()

    def run_until_completed(self, order: Order) -> bool:
        """Run ticks until the order is delivered or the limit is reached.

        Args:
            order: The order to wait for.

        Returns:
            True if the order was completed.
        """
        limit = int(self.config["max_ticks_per_order"])
        ticks = 0
        while order.status != Order.COMPLETED and ticks < limit:
            self.tick()
            ticks += 1
        return order.status == Order.COMPLETED

    def rider_by_id(self, rider_id: int) -> Optional[Rider]:
        """Return the rider with the given id, or None."""
        for rider in self.riders:
            if rider.rider_id == rider_id:
                return rider
        return None

    def to_dict(self) -> Dict[str, Any]:
        """Return a JSON-serialisable snapshot of the system state."""
        return {
            "funds": self.funds,
            "rider_id_counter": self.rider_id_counter,
            "current_tick": self.current_tick,
            "config": self.config,
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
            "orders": [o.to_dict() for o in self.order_manager.orders],
            "pending_order_ids": [o.id for o in self.order_manager.pending],
        }

    def save(self, path: Optional[str] = None) -> bool:
        """Write the system state to a JSON file.

        Args:
            path: Destination file; defaults to the configured save file.

        Returns:
            True on success, False if the file could not be written.
        """
        target = path or str(self.config["save_file"])
        try:
            with open(target, "w", encoding="utf-8") as handle:
                json.dump(self.to_dict(), handle, indent=2)
        except (OSError, TypeError, ValueError) as exc:
            logger.error("Failed to save state to %s: %s", target, exc)
            return False
        logger.info("Saved state to %s", target)
        return True

    def shutdown(self, path: Optional[str] = None) -> None:
        """Stop the main loop and persist the state."""
        self.save(path)
        self.is_running = False


def init_system(config: Optional[Dict[str, Any]] = None) -> SystemManager:
    """Initialise global variables and create the system manager.

    Args:
        config: Optional parameter overrides.

    Returns:
        The initialised SystemManager, also stored as global "system".
    """
    globalvar._init()
    manager = SystemManager(config)
    globalvar.set_value("system", manager)
    logger.info("System initialised")
    return manager
