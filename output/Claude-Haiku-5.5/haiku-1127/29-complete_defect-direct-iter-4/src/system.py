"""System-level orchestration: funds, rider recruitment and the tick loop.

Rider recruitment rule: when the system funds are at or above the hire
threshold (default 300), one new rider is created and the hire cost
(default 300) is deducted from the funds.
"""

import logging
from typing import Any, Dict, List, Optional

import globalvar
from order import OrderManager
from path_planner import GRID_SIZE
from persistence import load_config, save_state
from rider import STATE_DELIVERING, STATE_IDLE, STATE_NAMES, STATE_PICKING_UP, Rider

logger = logging.getLogger(__name__)


def init_system(config_path: Optional[str] = None) -> Dict[str, int]:
    """Initialise global variables and system parameters.

    Args:
        config_path: Optional JSON configuration file.

    Returns:
        The loaded configuration dictionary.
    """
    config = load_config(config_path)
    globalvar._init()
    globalvar.set_value("config", config)
    globalvar.set_value("funds", config["initial_funds"])
    globalvar.set_value("riders", [])
    globalvar.set_value("rider_id_counter", 0)
    globalvar.set_value("running", True)
    globalvar.set_value("time", 0)
    globalvar.set_value("orders", [])
    globalvar.set_value("order_counter", 0)
    logger.info("System initialised with config %s", config)
    return config


class SystemManager:
    """Owns funds, riders, orders and the simulation clock."""

    def __init__(self, config_path: Optional[str] = None) -> None:
        """Initialise the system.

        Args:
            config_path: Optional JSON configuration file path.
        """
        self.config: Dict[str, int] = init_system(config_path)
        self.orders = OrderManager()

    @property
    def funds(self) -> int:
        """Current fund balance (may be negative)."""
        return int(globalvar.get_value("funds", 0) or 0)

    def add_funds(self, amount: int) -> None:
        """Adjust the fund balance by ``amount`` (may be negative)."""
        globalvar.set_value("funds", self.funds + int(amount))

    @property
    def riders(self) -> List[Rider]:
        """The dynamic list of riders."""
        return globalvar.get_value("riders")

    @property
    def current_time(self) -> int:
        """Current simulated tick."""
        return int(globalvar.get_value("time", 0) or 0)

    def is_running(self) -> bool:
        """Return the main loop control flag."""
        return bool(globalvar.get_value("running", False))

    def stop(self) -> None:
        """Request that the main loop terminates."""
        globalvar.set_value("running", False)

    def get_rider(self, rider_id: int) -> Optional[Rider]:
        """Return the rider with the given id, or None."""
        for rider in self.riders:
            if rider.rider_id == rider_id:
                return rider
        return None

    def create_rider(self) -> Rider:
        """Create a new idle rider at the depot (0, 0) and register it.

        Returns:
            The newly created Rider.
        """
        rider_id = int(globalvar.get_value("rider_id_counter", 0) or 0) + 1
        globalvar.set_value("rider_id_counter", rider_id)
        rider = Rider(rider_id, x=0, y=0, speed=int(self.config["rider_speed"]))
        self.riders.append(rider)
        logger.info("Rider %d recruited", rider_id)
        return rider

    def can_accept_order(self) -> bool:
        """Return True if at least one rider exists or one can be recruited."""
        return bool(self.riders) or self.funds >= self.config["hire_threshold"]

    def try_recruit(self) -> Optional[Rider]:
        """Recruit a rider if the funds reach the hire threshold.

        Returns:
            The new Rider, or None if funds were insufficient.
        """
        if self.funds >= self.config["hire_threshold"]:
            self.add_funds(-self.config["hire_cost"])
            return self.create_rider()
        return None

    def tick(self, steps: int = 1) -> None:
        """Advance the simulation clock and move every rider.

        Each tick increments the simulated time by one and calls ``move()``
        on all riders. A failing rider is re-planned instead of crashing the
        whole simulation (error recovery).

        Args:
            steps: Number of ticks to simulate (>= 1).

        Raises:
            ValueError: If steps is less than one.
        """
        if steps < 1:
            raise ValueError("steps must be at least 1")
        for _ in range(steps):
            globalvar.set_value("time", self.current_time + 1)
            for rider in list(self.riders):
                try:
                    rider.move()
                except Exception:  # noqa: BLE001 - recovery path
                    logger.exception("Rider %d failed; re-planning", rider.rider_id)
                    rider.replan()

    def check_consistency(self) -> List[str]:
        """Check internal invariants and return a list of problems found.

        Returns:
            Human readable descriptions of inconsistencies (empty if none).
        """
        issues: List[str] = []
        ids = [rider.rider_id for rider in self.riders]
        if len(ids) != len(set(ids)):
            issues.append("Duplicate rider ids detected")
        if ids and max(ids) > int(globalvar.get_value("rider_id_counter", 0) or 0):
            issues.append("Rider id counter is behind issued rider ids")
        for rider in self.riders:
            if rider.state not in STATE_NAMES:
                issues.append(f"Rider {rider.rider_id} has invalid state {rider.state}")
            if rider.state in (STATE_PICKING_UP, STATE_DELIVERING) and not rider.orders:
                issues.append(f"Rider {rider.rider_id} is busy without orders")
            if not (0 <= rider.x <= GRID_SIZE and 0 <= rider.y <= GRID_SIZE):
                issues.append(f"Rider {rider.rider_id} is outside the map")
            if rider.state == STATE_IDLE and rider.orders:
                issues.append(f"Rider {rider.rider_id} is idle with queued orders")
        for issue in issues:
            logger.warning(issue)
        return issues

    def snapshot(self) -> Dict[str, Any]:
        """Return a JSON-serialisable snapshot of the whole system."""
        return {
            "time": self.current_time,
            "funds": self.funds,
            "config": dict(self.config),
            "riders": [rider.to_dict() for rider in self.riders],
            "orders": [order.to_dict() for order in self.orders.all_orders()],
        }

    def save(self, path: str) -> None:
        """Persist the current snapshot to a JSON file.

        Args:
            path: Destination file path.
        """
        save_state(path, self.snapshot())
