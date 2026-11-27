"""System manager: funds, rider recruitment, dispatch, ticking, persistence."""

import json
import logging
import os
from typing import Any, Dict, List, Optional, Tuple

import globalvar
from globalvar import get_value, set_value
from order import OrderManager, find_best_rider_for_order
from path_planner import PathPlanner
from rider import Rider

logger = logging.getLogger(__name__)

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEFAULT_CONFIG_PATH = os.path.join(PROJECT_ROOT, "config.json")
DEFAULT_STATE_PATH = os.path.join(PROJECT_ROOT, "simulation_state.json")

DEFAULT_CONFIG: Dict[str, int] = {
    "initial_funds": 1000,
    "recruitment_cost": 100,
    "max_rider_load": 3,
    "max_ticks_per_command": 1000,
}


def load_config(path: Optional[str] = None) -> Dict[str, int]:
    """Load system parameters from a JSON file, falling back to defaults.

    Unknown keys are ignored; invalid values are reported and replaced with
    defaults so that a bad configuration never stops the program.

    Args:
        path (str | None): Path to the JSON configuration file.

    Returns:
        dict: Effective configuration values.
    """
    config = dict(DEFAULT_CONFIG)
    path = path or DEFAULT_CONFIG_PATH
    if not os.path.exists(path):
        logger.info("No configuration file at %s; using defaults.", path)
        return config
    try:
        with open(path, "r", encoding="utf-8") as handle:
            data = json.load(handle)
    except (OSError, ValueError) as exc:
        logger.warning("Could not read configuration %s: %s", path, exc)
        return config
    if not isinstance(data, dict):
        logger.warning("Configuration %s must be a JSON object.", path)
        return config
    for key in DEFAULT_CONFIG:
        if key not in data:
            continue
        value = data[key]
        if isinstance(value, int) and not isinstance(value, bool) and value >= 0:
            config[key] = value
        else:
            logger.warning("Invalid value for %s in configuration; "
                           "using default.", key)
    return config


class SystemManager:
    """Core coordinator of the simulation.

    Attributes:
        recruitmentCost (int): Cost deducted from funds per new rider.
        orderManager (OrderManager): Order creation and assignment.
        planner (PathPlanner): Shared planner for route projections.
        config (dict): Effective configuration.
    """

    def __init__(self, config: Optional[Dict[str, int]] = None):
        """Initialise global state from configuration.

        Args:
            config (dict | None): Parameter overrides; defaults are used for
                missing keys.
        """
        cfg = dict(DEFAULT_CONFIG)
        cfg.update(config or {})
        self.config = cfg
        self.recruitmentCost = int(cfg["recruitment_cost"])
        self.orderManager = OrderManager()
        self.planner = PathPlanner()
        set_value("funds", int(cfg["initial_funds"]))
        set_value("riders", [])
        set_value("rider_id_counter", 0)
        set_value("is_running", True)
        set_value("current_tick", 0)
        set_value("orders", [])
        set_value("order_history", [])
        set_value("order_id_counter", 0)
        set_value("max_rider_load", int(cfg["max_rider_load"]))

    @property
    def funds(self) -> int:
        """int: Current system funds (may be negative)."""
        return int(get_value("funds", 0))

    @funds.setter
    def funds(self, value: int) -> None:
        set_value("funds", int(value))

    @property
    def riderIdCounter(self) -> int:
        """int: Last issued rider id."""
        return int(get_value("rider_id_counter", 0))

    @riderIdCounter.setter
    def riderIdCounter(self, value: int) -> None:
        set_value("rider_id_counter", int(value))

    @property
    def isRunning(self) -> bool:
        """bool: Main loop control flag."""
        return bool(get_value("is_running", False))

    @isRunning.setter
    def isRunning(self, value: bool) -> None:
        set_value("is_running", bool(value))

    @property
    def currentTick(self) -> int:
        """int: Current simulated tick."""
        return int(get_value("current_tick", 0))

    @currentTick.setter
    def currentTick(self, value: int) -> None:
        set_value("current_tick", int(value))

    @property
    def riders(self) -> List[Rider]:
        """list[Rider]: The dynamic rider list."""
        return get_value("riders")

    def stop(self) -> None:
        """Request that the main loop terminate."""
        self.isRunning = False
        logger.info("System stop requested.")

    def can_afford_rider(self) -> bool:
        """Return True if funds cover the recruitment cost.

        Returns:
            bool: Affordability flag.
        """
        return self.funds >= self.recruitmentCost

    def recruit_rider(self) -> Optional[Rider]:
        """Recruit a new rider if funds allow.

        Returns:
            Rider | None: The new rider, or None when funds are insufficient.
        """
        if not self.can_afford_rider():
            logger.info("Recruitment skipped: insufficient funds (%s).",
                        self.funds)
            return None
        self.funds = self.funds - self.recruitmentCost
        self.riderIdCounter = self.riderIdCounter + 1
        rider = Rider(self.riderIdCounter)
        self.riders.append(rider)
        logger.info("Recruited rider %s; funds now %s.", rider.rider_id,
                    self.funds)
        return rider

    def dispatch_order(self, restaurant, customer
                       ) -> Tuple[Any, Rider, bool]:
        """Create an order and assign it, recruiting a rider if needed.

        Args:
            restaurant (Sequence[int]): Restaurant ``[x, y]``.
            customer (Sequence[int]): Customer ``[x, y]``.

        Returns:
            tuple[Order, Rider, bool]: The order, the assigned rider, and
            True when a new rider was recruited for this order.

        Raises:
            RuntimeError: If no rider has spare capacity and a new rider
                cannot be afforded.
        """
        order = self.orderManager.create_order(restaurant, customer)
        rider = find_best_rider_for_order(order)
        new_rider = False
        if rider is None:
            rider = self.recruit_rider()
            if rider is None:
                self.orderManager.discard_order(order)
                raise RuntimeError(
                    "No rider is available and funds are insufficient "
                    "to recruit a new rider.")
            new_rider = True
        self.orderManager.assign_order(order, rider)
        return order, rider, new_rider

    def tick(self, steps: int = 1) -> int:
        """Advance the simulation by one or more ticks.

        Each tick increments the clock and moves every rider. Exceptions
        raised by a rider are logged and the rider is recovered so that one
        faulty rider cannot stop the simulation.

        Args:
            steps (int): Number of ticks to simulate.

        Returns:
            int: The tick number after advancing.
        """
        for _ in range(max(0, int(steps))):
            self.currentTick = self.currentTick + 1
            for rider in list(self.riders):
                try:
                    rider.move()
                except Exception:  # noqa: BLE001 - recovery path
                    logger.exception("Rider %s failed; recovering.",
                                     rider.rider_id)
                    rider.recover()
        return self.currentTick

    def check_consistency(self) -> List[str]:
        """Verify internal invariants and report problems.

        Returns:
            list[str]: Human-readable issues; empty when the state is valid.
        """
        issues: List[str] = []
        ids = [r.rider_id for r in self.riders]
        if len(ids) != len(set(ids)):
            issues.append("duplicate rider ids detected")
        for rider in self.riders:
            for order in rider.orders:
                if order.rider_id != rider.rider_id:
                    issues.append(f"order {order.id} is held by rider "
                                  f"{rider.rider_id} but records "
                                  f"{order.rider_id}")
                if order.status == order.COMPLETED:
                    issues.append(f"completed order {order.id} still in "
                                  f"rider {rider.rider_id}'s list")
        return issues

    def snapshot(self) -> Dict[str, Any]:
        """Return a JSON-compatible snapshot of the whole system.

        Returns:
            dict: Configuration, funds, tick, riders, and orders.
        """
        return {
            "config": self.config,
            "funds": self.funds,
            "current_tick": self.currentTick,
            "rider_id_counter": self.riderIdCounter,
            "riders": [r.to_dict() for r in self.riders],
            "orders": self.orderManager.to_dict_list(),
        }

    def save_state(self, path: Optional[str] = None) -> str:
        """Persist the system snapshot as JSON using an atomic write.

        Args:
            path (str | None): Destination file; defaults to
                ``simulation_state.json`` in the project root.

        Returns:
            str: Path of the written file.

        Raises:
            OSError: If the file cannot be written.
        """
        path = path or DEFAULT_STATE_PATH
        temp_path = path + ".tmp"
        with open(temp_path, "w", encoding="utf-8") as handle:
            json.dump(self.snapshot(), handle, indent=2)
        os.replace(temp_path, path)
        logger.info("State saved to %s", path)
        return path


def init_system(config_path: Optional[str] = None) -> SystemManager:
    """Initialise global variables and create the system manager.

    Args:
        config_path (str | None): Optional configuration file path.

    Returns:
        SystemManager: The initialised system.
    """
    globalvar._init()
    config = load_config(config_path)
    manager = SystemManager(config)
    logger.info("System initialised with funds %s.", manager.funds)
    return manager
