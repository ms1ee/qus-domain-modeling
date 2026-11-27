"""System initialisation and the SystemManager core class.

SystemManager owns the business rules: funds, automatic rider recruitment,
order dispatch and the simulation clock. All mutable state lives in globalvar.
"""

import json
import logging
import os
from typing import Any, Dict, List, Optional, Tuple

import globalvar
from order import OrderManager
from order_model import STATUS_COMPLETED, STATUS_PENDING, Order
from rider import STATE_IDLE, Rider

logger = logging.getLogger(__name__)

DEFAULT_CONFIG: Dict[str, int] = {
    "initial_funds": 1000,
    "recruit_cost": 300,
    "recruit_min_funds": 300,
}

CONFIG_FILE = os.path.normpath(
    os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "config.json")
)

MAX_TICKS_PER_COMMAND = 1000


def _load_config(path: str) -> Dict[str, int]:
    """Load system parameters from a JSON file, falling back to defaults.

    Args:
        path: Path to the JSON configuration file.

    Returns:
        Configuration dictionary containing every key in DEFAULT_CONFIG.
    """
    config = dict(DEFAULT_CONFIG)
    if not os.path.isfile(path):
        return config
    try:
        with open(path, encoding="utf-8") as handle:
            data = json.load(handle)
    except (OSError, json.JSONDecodeError) as exc:
        logger.warning("Could not read config %s: %s; using defaults", path, exc)
        return config
    if not isinstance(data, dict):
        logger.warning("Config %s must contain a JSON object; using defaults", path)
        return config
    for key in DEFAULT_CONFIG:
        value = data.get(key)
        if isinstance(value, int) and not isinstance(value, bool):
            config[key] = value
    return config


def init_system() -> "SystemManager":
    """Initialise global variables and return the system manager.

    Sets system funds (from the configuration, default 1000), an empty rider
    list, rider ID counter 0, the running flag True and simulated time 0.

    Returns:
        A ready-to-use SystemManager instance.
    """
    globalvar._init()
    config = _load_config(CONFIG_FILE)
    globalvar.set_value("config", config)
    globalvar.set_value("system_funds", int(config["initial_funds"]))
    globalvar.set_value("riders", [])
    globalvar.set_value("rider_id_counter", 0)
    globalvar.set_value("running", True)
    globalvar.set_value("time", 0)
    globalvar.set_value("orders", [])
    logger.info("System initialised with funds=%s", config["initial_funds"])
    return SystemManager()


class SystemManager:
    """Core manager for funds, riders, dispatching and the simulation clock."""

    def __init__(self) -> None:
        """Create the manager bound to the global state."""
        self.order_manager = OrderManager()

    # ----------------------------------------------------------- properties
    @property
    def config(self) -> Dict[str, int]:
        """System configuration parameters."""
        return globalvar.get_value("config", dict(DEFAULT_CONFIG)) or dict(DEFAULT_CONFIG)

    @property
    def funds(self) -> int:
        """Current system fund balance (may be negative)."""
        return int(globalvar.get_value("system_funds", 0))

    @funds.setter
    def funds(self, value: int) -> None:
        globalvar.set_value("system_funds", int(value))

    @property
    def riders(self) -> List[Rider]:
        """Riders currently in service."""
        riders = globalvar.get_value("riders")
        if riders is None:
            riders = []
            globalvar.set_value("riders", riders)
        return riders

    @property
    def time(self) -> int:
        """Current simulation tick."""
        return int(globalvar.get_value("time", 0) or 0)

    @property
    def running(self) -> bool:
        """Main loop control flag."""
        return bool(globalvar.get_value("running", False))

    def stop(self) -> None:
        """Clear the running flag so the main loop exits."""
        globalvar.set_value("running", False)

    # ---------------------------------------------------------- queries
    def idle_riders(self) -> List[Rider]:
        """Return riders with state idle and no assigned orders."""
        return [rider for rider in self.riders if rider.is_idle()]

    def find_rider(self, rider_id: int) -> Optional[Rider]:
        """Return the rider with the given ID, or None."""
        for rider in self.riders:
            if rider.rider_id == rider_id:
                return rider
        return None

    # ---------------------------------------------------- recruitment
    def should_recruit(self, pending_count: int) -> bool:
        """Decide whether a new rider must be recruited.

        Recruitment happens when funds are at least the minimum threshold
        (300) and the number of pending orders exceeds the number of idle riders.

        Args:
            pending_count: Number of orders waiting for a rider.

        Returns:
            True if a rider should be recruited.
        """
        return (
            self.funds >= int(self.config["recruit_min_funds"])
            and pending_count > len(self.idle_riders())
        )

    def recruit_rider(self) -> Rider:
        """Create a new rider and deduct the recruitment cost.

        Returns:
            The newly recruited rider.
        """
        cost = int(self.config["recruit_cost"])
        self.funds -= cost
        counter = int(globalvar.get_value("rider_id_counter", 0) or 0) + 1
        globalvar.set_value("rider_id_counter", counter)
        rider = Rider(counter)
        self.riders.append(rider)
        logger.info("Recruited rider #%d for %d (funds now %d)", counter, cost, self.funds)
        return rider

    def _ensure_capacity(self) -> bool:
        """Recruit one rider if the recruitment rule applies."""
        pending = len(self.order_manager.pending_orders())
        if self.should_recruit(pending):
            self.recruit_rider()
            return True
        return False

    # ---------------------------------------------------- dispatching
    def submit_order(self, res_pos, cus_pos) -> Dict[str, Any]:
        """Create an order, recruit if needed and assign it to a rider.

        Args:
            res_pos: Restaurant coordinates ``[x, y]`` (0-800).
            cus_pos: Customer coordinates ``[x, y]`` (0-800).

        Returns:
            Dictionary with keys "order" (Order), "rider" (Rider or None) and
            "new_rider" (bool, True if a rider was recruited for this order).
        """
        order: Order = self.order_manager.create_order(res_pos, cus_pos)
        new_rider = self._ensure_capacity()
        rider = self.order_manager.assign_order(order)
        return {"order": order, "rider": rider, "new_rider": new_rider}

    def dispatch_pending(self) -> bool:
        """Try to assign every pending order, recruiting riders when allowed.

        Returns:
            True if at least one rider was recruited during the call.
        """
        recruited = False
        for order in self.order_manager.pending_orders():
            if self._ensure_capacity():
                recruited = True
            if self.order_manager.assign_order(order) is None:
                break
        return recruited

    # ---------------------------------------------------- simulation
    def tick(self) -> None:
        """Advance the simulation by one unit of time.

        Increments the clock, dispatches pending orders, then moves every rider.
        A failure in one rider is logged and does not stop the others.
        """
        globalvar.set_value("time", self.time + 1)
        try:
            self.dispatch_pending()
        except Exception:  # pragma: no cover - defensive recovery
            logger.exception("Dispatch failed at tick %d", self.time)
        for rider in list(self.riders):
            try:
                rider.move()
            except Exception:  # pragma: no cover - defensive recovery
                logger.exception("Rider #%d failed at tick %d", rider.rider_id, self.time)

    def check_consistency(self) -> List[str]:
        """Verify internal invariants and return a list of problems found.

        Returns:
            Human readable problem descriptions; empty when consistent.
        """
        problems: List[str] = []
        rider_ids = {rider.rider_id for rider in self.riders}
        for rider in self.riders:
            if rider.state != STATE_IDLE and not rider.orders:
                problems.append(f"Rider #{rider.rider_id} is {rider.state_name} without orders")
            for order in rider.orders:
                if order.rider_id != rider.rider_id:
                    problems.append(
                        f"Order #{order.id} is queued on rider #{rider.rider_id} "
                        f"but records rider #{order.rider_id}"
                    )
        for order in self.order_manager.all_orders():
            if order.status not in (STATUS_PENDING, STATUS_COMPLETED):
                if order.rider_id not in rider_ids:
                    problems.append(f"Order #{order.id} references missing rider {order.rider_id}")
        return problems

    # ---------------------------------------------------- persistence
    def save_state(self, path: str) -> None:
        """Write the system parameters, riders and orders to a JSON file.

        Args:
            path: Destination file path.

        Raises:
            OSError: If the file cannot be written.
        """
        state = {
            "time": self.time,
            "system_funds": self.funds,
            "config": self.config,
            "riders": [rider.to_dict() for rider in self.riders],
            "orders": [order.to_dict() for order in self.order_manager.all_orders()],
        }
        with open(path, "w", encoding="utf-8") as handle:
            json.dump(state, handle, indent=2)
        logger.info("State saved to %s", path)
