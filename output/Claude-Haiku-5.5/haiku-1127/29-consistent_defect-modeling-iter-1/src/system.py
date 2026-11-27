"""System-level state management: funds, riders, recruitment and time ticks."""

import json
import logging
from typing import Any, Dict, List, Optional, Tuple

from globalvar import _init, get_value, set_value
from order import OrderManager
from order_model import Order
from rider import Rider

logger = logging.getLogger(__name__)

DEFAULT_CONFIG: Dict[str, Any] = {
    "initial_funds": 1000,
    "recruit_threshold": 300,
    "recruit_cost": 500,
    "rider_speed": 20,
    "spawn_x": 400,
    "spawn_y": 400,
    "map_size": 800,
    "cell_size": 100,
}


def init_system() -> None:
    """Initialise global variables and default configuration.

    Sets funds=1000, empty rider list, rider id counter=0, running=True,
    simulated_time=0 and an empty order list.
    """
    _init()
    set_value("config", dict(DEFAULT_CONFIG))
    set_value("funds", int(DEFAULT_CONFIG["initial_funds"]))
    set_value("riders", [])
    set_value("rider_id_counter", 0)
    set_value("running", True)
    set_value("simulated_time", 0)
    set_value("orders", [])
    logger.info("System initialised")


def _config(key: str) -> Any:
    """Return a configuration value by key."""
    config = get_value("config") or DEFAULT_CONFIG
    return config.get(key, DEFAULT_CONFIG[key])


def load_config(path: str) -> Dict[str, Any]:
    """Override system parameters from a JSON configuration file.

    Only keys present in DEFAULT_CONFIG are accepted.

    Args:
        path: Path to a JSON object file.

    Returns:
        The effective configuration dictionary.

    Raises:
        ValueError: If the file does not contain a JSON object.
    """
    with open(path, "r", encoding="utf-8") as handle:
        data = json.load(handle)
    if not isinstance(data, dict):
        raise ValueError("Configuration file must contain a JSON object.")
    config = dict(get_value("config") or DEFAULT_CONFIG)
    for key in DEFAULT_CONFIG:
        if key in data:
            config[key] = int(data[key])
    set_value("config", config)
    logger.info("Configuration loaded from %s", path)
    return config


class SystemManager:
    """Core coordinator for funds, riders, recruitment and simulation ticks.

    All state is held in the global variable store so that other modules
    observe the same values.
    """

    def __init__(self) -> None:
        self.order_manager = OrderManager()

    # ------------------------------------------------------------------ #
    # Properties backed by globalvar
    # ------------------------------------------------------------------ #
    @property
    def funds(self) -> int:
        """Current system funds (may be negative)."""
        return int(get_value("funds", 0))

    @funds.setter
    def funds(self, value: int) -> None:
        set_value("funds", int(value))

    @property
    def riders(self) -> List[Rider]:
        """Dynamic list of riders."""
        return get_value("riders")

    @property
    def rider_id_counter(self) -> int:
        """Last issued rider identifier."""
        return int(get_value("rider_id_counter", 0))

    @rider_id_counter.setter
    def rider_id_counter(self, value: int) -> None:
        set_value("rider_id_counter", int(value))

    @property
    def running(self) -> bool:
        """Main loop control flag."""
        return bool(get_value("running", False))

    @property
    def simulated_time(self) -> int:
        """Number of ticks elapsed."""
        return int(get_value("simulated_time", 0))

    def stop(self) -> None:
        """Request the main loop to terminate."""
        set_value("running", False)

    # ------------------------------------------------------------------ #
    # Rider resources
    # ------------------------------------------------------------------ #
    def create_rider(self) -> Rider:
        """Recruit a new rider, deducting the recruitment cost.

        Returns:
            The newly created Rider, spawned at the configured location.
        """
        self.rider_id_counter = self.rider_id_counter + 1
        self.funds = self.funds - int(_config("recruit_cost"))
        rider = Rider(
            self.rider_id_counter,
            x=int(_config("spawn_x")),
            y=int(_config("spawn_y")),
            speed=int(_config("rider_speed")),
        )
        self.riders.append(rider)
        logger.info("Recruited rider %s; funds now %s", rider.rider_id, self.funds)
        return rider

    def idle_rider_count(self) -> int:
        """Return the number of riders without active orders."""
        return sum(1 for r in self.riders if r.is_available())

    def should_recruit(self, pending_count: int) -> bool:
        """Return True if a new rider should be recruited.

        Trigger: funds >= threshold AND pending orders > idle riders.
        """
        return self.funds >= int(_config("recruit_threshold")) and pending_count > self.idle_rider_count()

    def dispatch_order(self, order: Order) -> Tuple[Optional[Rider], bool]:
        """Recruit if needed, then assign ``order`` to the best rider.

        Returns:
            Tuple of (assigned rider or None, whether a rider was recruited).
        """
        recruited = False
        while self.should_recruit(len(self.order_manager.pending_orders())):
            self.create_rider()
            recruited = True
        rider = self.order_manager.assign_order(order)
        return rider, recruited

    def retry_pending(self) -> None:
        """Try to dispatch orders that could not be assigned earlier."""
        for order in self.order_manager.pending_orders():
            self.dispatch_order(order)

    # ------------------------------------------------------------------ #
    # Simulation
    # ------------------------------------------------------------------ #
    def tick(self) -> None:
        """Advance simulated time by one unit and move every rider."""
        set_value("simulated_time", self.simulated_time + 1)
        self.retry_pending()
        for rider in list(self.riders):
            rider.move()

    def run_ticks(self, count: int) -> None:
        """Run ``count`` consecutive ticks."""
        for _ in range(count):
            self.tick()

    # ------------------------------------------------------------------ #
    # Persistence
    # ------------------------------------------------------------------ #
    def save_state(self, path: str) -> None:
        """Write configuration, riders and orders to a JSON file."""
        data = {
            "config": get_value("config") or DEFAULT_CONFIG,
            "funds": self.funds,
            "rider_id_counter": self.rider_id_counter,
            "simulated_time": self.simulated_time,
            "riders": [r.to_dict() for r in self.riders],
            "orders": [o.to_dict() for o in self.order_manager.orders()],
        }
        with open(path, "w", encoding="utf-8") as handle:
            json.dump(data, handle, indent=2)
        logger.info("State saved to %s", path)
