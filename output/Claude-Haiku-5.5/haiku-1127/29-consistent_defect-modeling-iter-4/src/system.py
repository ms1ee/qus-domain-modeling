"""System-level state management, recruitment and the simulation tick loop."""

import json
import logging
import os
from typing import Any, Dict, List, Optional, Sequence

import globalvar
from order import OrderManager
from order_model import Order
from rider import STATE_IDLE, Rider

logger = logging.getLogger(__name__)

DEFAULT_CONFIG: Dict[str, Any] = {
    "initial_funds": 1000,
    "recruit_min_funds": 300,
    "recruit_cost": 500,
    "max_ticks_per_command": 10000,
}


class SystemManager:
    """Manages funds, riders, orders and simulated time.

    Shared values are stored in the ``globalvar`` store so that other
    modules can access them. Properties provide typed access.
    """

    def __init__(self) -> None:
        """Bind to the global store and load the configuration."""
        if globalvar.get_value("riders") is None:
            globalvar.set_value("riders", [])
        self.config: Dict[str, Any] = globalvar.get_value("config") or dict(DEFAULT_CONFIG)

    @property
    def funds(self) -> int:
        """System funds (may be negative)."""
        return int(globalvar.get_value("funds", 0))

    @funds.setter
    def funds(self, value: int) -> None:
        globalvar.set_value("funds", int(value))

    @property
    def rider_id_counter(self) -> int:
        """Last issued rider ID."""
        return int(globalvar.get_value("rider_id_counter", 0))

    @rider_id_counter.setter
    def rider_id_counter(self, value: int) -> None:
        globalvar.set_value("rider_id_counter", int(value))

    @property
    def is_running(self) -> bool:
        """Main loop control flag."""
        return bool(globalvar.get_value("is_running", True))

    @is_running.setter
    def is_running(self, value: bool) -> None:
        globalvar.set_value("is_running", bool(value))

    @property
    def simulated_time(self) -> int:
        """Current simulated tick."""
        return int(globalvar.get_value("simulated_time", 0))

    @simulated_time.setter
    def simulated_time(self, value: int) -> None:
        globalvar.set_value("simulated_time", int(value))

    @property
    def riders(self) -> List[Rider]:
        """The dynamic list of riders."""
        return globalvar.get_value("riders")

    @property
    def order_manager(self) -> OrderManager:
        """The order manager instance."""
        return globalvar.get_value("order_manager")

    def get_rider(self, rider_id: int) -> Optional[Rider]:
        """Return the rider with ``rider_id``, or None.

        Args:
            rider_id: Rider identifier.
        """
        for rider in self.riders:
            if rider.rider_id == rider_id:
                return rider
        return None

    def idle_riders(self) -> List[Rider]:
        """Return riders whose state is idle."""
        return [rider for rider in self.riders if rider.state == STATE_IDLE]

    def create_rider(self) -> Rider:
        """Create a new rider at the default location and register it.

        Returns:
            The newly created Rider.
        """
        self.rider_id_counter = self.rider_id_counter + 1
        rider = Rider(self.rider_id_counter)
        self.riders.append(rider)
        return rider

    def maybe_recruit(self, pending_count: int) -> Optional[Rider]:
        """Recruit a rider if funds allow and pending orders exceed idle riders.

        Args:
            pending_count: Number of orders waiting for a rider.

        Returns:
            The new Rider, or None if no recruitment happened.
        """
        min_funds = int(self.config["recruit_min_funds"])
        cost = int(self.config["recruit_cost"])
        if self.funds >= min_funds and pending_count > len(self.idle_riders()):
            rider = self.create_rider()
            self.funds = self.funds - cost
            logger.info("Recruited rider #%d (funds now %d)", rider.rider_id, self.funds)
            return rider
        return None

    def dispatch_pending(self) -> List[Order]:
        """Assign every pending order, recruiting riders when required.

        Returns:
            Orders that were assigned during this call.
        """
        manager = self.order_manager
        assigned: List[Order] = []
        for order in manager.pending_orders():
            self.maybe_recruit(len(manager.pending_orders()))
            if manager.assign(order) is not None:
                assigned.append(order)
        return assigned

    def submit_order(self, res_pos: Sequence[int], cus_pos: Sequence[int]) -> Dict[str, Any]:
        """Create an order and dispatch it.

        Args:
            res_pos: Restaurant point ``(x, y)``.
            cus_pos: Customer point ``(x, y)``.

        Returns:
            Dictionary with keys ``order``, ``rider`` (may be None) and
            ``new_rider`` (bool).

        Raises:
            ValueError: If coordinates are invalid.
        """
        riders_before = len(self.riders)
        order = self.order_manager.create_order(res_pos, cus_pos, self.simulated_time)
        self.dispatch_pending()
        rider = self.get_rider(order.rider_id) if order.rider_id is not None else None
        return {
            "order": order,
            "rider": rider,
            "new_rider": len(self.riders) > riders_before,
        }

    def tick(self) -> List[Dict[str, Any]]:
        """Advance the simulation by one tick.

        Pending orders are dispatched first, then every rider moves.

        Returns:
            Log entries produced during this tick (each contains ``rider_id``).
        """
        self.simulated_time = self.simulated_time + 1
        self.dispatch_pending()
        events: List[Dict[str, Any]] = []
        for rider in list(self.riders):
            start = len(rider.log)
            rider.move()
            events.extend(rider.log[start:])
        return events

    def run_ticks(self, count: int) -> List[Dict[str, Any]]:
        """Advance the simulation by ``count`` ticks.

        Args:
            count: Number of ticks to run.

        Returns:
            All events produced during the run.

        Raises:
            ValueError: If ``count`` is outside the allowed range.
        """
        limit = int(self.config.get("max_ticks_per_command", 10000))
        if not 1 <= count <= limit:
            raise ValueError(f"tick count must be between 1 and {limit}")
        events: List[Dict[str, Any]] = []
        for _ in range(count):
            events.extend(self.tick())
        for problem in self.check_consistency():
            logger.warning("Consistency check: %s", problem)
        return events

    def check_consistency(self) -> List[str]:
        """Check internal invariants and return a list of problems found.

        Returns:
            Human readable problem descriptions (empty when consistent).
        """
        problems: List[str] = []
        rider_ids = [rider.rider_id for rider in self.riders]
        if len(set(rider_ids)) != len(rider_ids):
            problems.append("duplicate rider IDs detected")
        for rider in self.riders:
            has_orders = bool(rider.active_orders())
            if rider.state == STATE_IDLE and has_orders:
                problems.append(f"rider #{rider.rider_id} is idle but has active orders")
            if rider.state != STATE_IDLE and not has_orders:
                problems.append(f"rider #{rider.rider_id} is busy without orders")
        known = set(rider_ids)
        for order in self.order_manager.orders:
            if order.rider_id is not None and order.rider_id not in known:
                problems.append(f"order #{order.id} references unknown rider")
        return problems

    def to_dict(self) -> Dict[str, Any]:
        """Return a JSON-serialisable snapshot of the whole system."""
        return {
            "funds": self.funds,
            "simulated_time": self.simulated_time,
            "rider_id_counter": self.rider_id_counter,
            "config": self.config,
            "riders": [rider.to_dict() for rider in self.riders],
            "orders": [order.to_dict() for order in self.order_manager.orders],
        }

    def save_state(self, path: str) -> None:
        """Write the system snapshot to a JSON file.

        Args:
            path: Destination file path.

        Raises:
            OSError: If the file cannot be written.
        """
        with open(path, "w", encoding="utf-8") as handle:
            json.dump(self.to_dict(), handle, indent=2)
        logger.info("State saved to %s", path)


def _load_config(config_path: Optional[str]) -> Dict[str, Any]:
    """Load configuration overrides from a JSON file.

    Missing or malformed files fall back to the defaults.

    Args:
        config_path: Path to the JSON configuration file, or None.

    Returns:
        The effective configuration dictionary.
    """
    config = dict(DEFAULT_CONFIG)
    if not config_path:
        return config
    if not os.path.exists(config_path):
        logger.warning("Config file %s not found; using defaults", config_path)
        return config
    try:
        with open(config_path, "r", encoding="utf-8") as handle:
            loaded = json.load(handle)
        if not isinstance(loaded, dict):
            raise ValueError("configuration root must be an object")
        for key in DEFAULT_CONFIG:
            if key in loaded:
                config[key] = int(loaded[key])
    except (OSError, ValueError, TypeError) as exc:
        logger.error("Could not load config %s: %s; using defaults", config_path, exc)
        config = dict(DEFAULT_CONFIG)
    return config


def init_system(config_path: Optional[str] = None) -> SystemManager:
    """Initialise global state and return a ready SystemManager.

    Sets funds to the configured initial value, an empty rider list, rider
    ID counter 0, running state True and simulated time 0.

    Args:
        config_path: Optional JSON file with system parameter overrides.

    Returns:
        The initialised SystemManager.
    """
    globalvar._init()
    config = _load_config(config_path)
    globalvar.set_value("config", config)
    globalvar.set_value("funds", int(config["initial_funds"]))
    globalvar.set_value("riders", [])
    globalvar.set_value("rider_id_counter", 0)
    globalvar.set_value("is_running", True)
    globalvar.set_value("simulated_time", 0)
    globalvar.set_value("order_manager", OrderManager())
    logger.info("System initialised with funds=%d", config["initial_funds"])
    return SystemManager()
