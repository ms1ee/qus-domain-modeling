"""Core system manager: funds, rider recruitment, tick loop and persistence."""

import json
import logging
import os

import globalvar
from config import load_config
from order import OrderManager
from path_planner import PathPlanner
from rider import Rider

LOGGER = logging.getLogger("dispatch.system")


class SystemManager:
    """Owns the funds, the rider list, the order manager and the clock.

    Attributes:
        config: Effective configuration dictionary.
        funds: Integer fund balance (may be negative).
        riders: Dynamic list of Rider objects (also stored in globalvar).
        rider_id_counter: Last issued rider identifier.
        running_state: Boolean controlling the main loop.
        current_tick: Simulated time in ticks.
        order_manager: OrderManager instance.
        path_planner: PathPlanner instance used for route display.
    """

    def __init__(self, config: dict):
        """Create the system with the given configuration.

        Args:
            config: Configuration dictionary (see config.DEFAULT_CONFIG).
        """
        self.config = dict(config)
        self.config["hub_position"] = [int(v) for v in config["hub_position"]]
        self.funds = int(config["initial_funds"])
        self.riders = []
        self.rider_id_counter = 0
        self.running_state = True
        self.current_tick = 0
        self.order_manager = OrderManager()
        self.path_planner = PathPlanner()
        self._settled_orders = set()
        globalvar.set_value("riders", self.riders)
        globalvar.set_value("current_tick", self.current_tick)

    def add_funds(self, amount: int) -> None:
        """Adjust the fund balance by ``amount`` (negative values deduct).

        Args:
            amount: Integer amount to add.
        """
        self.funds += int(amount)

    def can_recruit(self) -> bool:
        """Return True when funds meet the threshold and the rider cap allows it.

        Returns:
            bool: Whether a new rider may be recruited now.
        """
        return (self.funds >= int(self.config["recruit_threshold"])
                and len(self.riders) < int(self.config["max_riders"]))

    def recruit_rider(self) -> Rider:
        """Create a new idle rider at the hub and charge the hiring cost.

        Returns:
            Rider: The newly created rider.
        """
        self.rider_id_counter += 1
        hub = tuple(self.config["hub_position"])
        rider = Rider(self.rider_id_counter,
                      speed=int(self.config["rider_speed"]),
                      position=hub)
        self.riders.append(rider)
        self.funds -= int(self.config["hire_cost"])
        LOGGER.info("Recruited rider %s", rider.rider_id)
        return rider

    def check_recruitment(self) -> bool:
        """Recruit a rider automatically if the recruitment condition holds.

        Returns:
            bool: True if a new rider was added.
        """
        if self.can_recruit():
            self.recruit_rider()
            return True
        return False

    def get_rider(self, rider_id: int):
        """Look up a rider by identifier.

        Args:
            rider_id: Rider identifier.

        Returns:
            Rider | None: The matching rider or None.
        """
        for rider in self.riders:
            if rider.rider_id == rider_id:
                return rider
        return None

    def remove_rider(self, rider_id: int) -> None:
        """Remove an idle rider that has no orders.

        Args:
            rider_id: Identifier of the rider to remove.

        Raises:
            ValueError: If the rider does not exist or is still busy.
        """
        rider = self.get_rider(rider_id)
        if rider is None:
            raise ValueError(f"rider #{rider_id} does not exist")
        if rider.orders or rider.state != 0:
            raise ValueError(f"rider #{rider_id} is busy and cannot be removed")
        self.riders.remove(rider)

    def tick(self) -> None:
        """Advance the whole simulation by one tick.

        Increments the clock, moves every rider (isolating failures per
        rider), then settles newly completed orders into the fund balance.
        """
        self.current_tick += 1
        globalvar.set_value("current_tick", self.current_tick)
        for rider in list(self.riders):
            try:
                rider.move()
            except Exception:  # error recovery: keep simulation running
                LOGGER.exception("Rider %s failed during tick; resetting", rider.rider_id)
                rider.reset()
        self._settle_completed_orders()

    def _settle_completed_orders(self) -> None:
        """Credit delivery fees and deduct fuel for newly completed orders."""
        settled_any = False
        for order in self.order_manager.orders:
            if order.status != "completed" or order.id in self._settled_orders:
                continue
            fee = int(self.config["delivery_fee"])
            fuel = order.distance * int(self.config["fuel_cost_per_100_units"]) // 100
            self.add_funds(fee - fuel)
            self._settled_orders.add(order.id)
            settled_any = True
        if settled_any:
            self.check_recruitment()

    def check_consistency(self) -> list:
        """Verify and repair rider state consistency.

        Returns:
            list[str]: Descriptions of issues found and repaired.
        """
        issues = []
        seen_ids = set()
        for rider in self.riders:
            if rider.rider_id in seen_ids:
                issues.append(f"duplicate rider id {rider.rider_id}")
            seen_ids.add(rider.rider_id)
            if rider.state not in (0, 1, 2):
                issues.append(f"rider {rider.rider_id} had invalid state {rider.state}")
                rider.state = 0
            if rider.state != 0 and not rider.orders:
                issues.append(f"rider {rider.rider_id} busy without orders")
                rider.reset()
            rider.x = min(max(rider.x, 0), 800)
            rider.y = min(max(rider.y, 0), 800)
        return issues

    def to_dict(self) -> dict:
        """Serialise the whole system state to a JSON-compatible dictionary.

        Returns:
            dict: Configuration, funds, clock, riders and order history.
        """
        return {
            "config": self.config,
            "funds": self.funds,
            "current_tick": self.current_tick,
            "rider_id_counter": self.rider_id_counter,
            "running_state": self.running_state,
            "riders": [rider.to_dict() for rider in self.riders],
            "orders": [order.to_dict() for order in self.order_manager.orders],
        }

    def save_state(self, path: str) -> bool:
        """Write the system state to a JSON file atomically.

        Args:
            path: Destination file path.

        Returns:
            bool: True on success, False if the file could not be written.
        """
        temp_path = path + ".tmp"
        try:
            with open(temp_path, "w", encoding="utf-8") as handle:
                json.dump(self.to_dict(), handle, indent=2)
            os.replace(temp_path, path)
            return True
        except (OSError, TypeError, ValueError) as exc:
            LOGGER.error("Failed to save state to %s: %s", path, exc)
            return False


def init_system(config: dict = None) -> SystemManager:
    """Initialise the global store and the system manager.

    Resets global variables, creates the SystemManager and recruits the
    first rider if the initial funds meet the recruitment threshold.

    Args:
        config: Optional configuration dictionary; defaults are used if None.

    Returns:
        SystemManager: The initialised system.
    """
    globalvar._init()
    effective = config if config is not None else load_config()
    manager = SystemManager(effective)
    manager.check_recruitment()
    return manager
