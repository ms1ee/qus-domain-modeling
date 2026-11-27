"""System management: configuration, funds, rider recruitment and ticks.

Persistence: configuration is read from a JSON file and the full simulation
state (funds, riders, order history) can be written to a JSON file.
"""

import json
import logging
import os

import globalvar
from order import OrderManager
from path_planner import MAP_SIZE, Grid
from rider import IDLE, Rider

logger = logging.getLogger(__name__)

DEFAULT_CONFIG_FILE = "config.json"

DEFAULT_CONFIG = {
    "initial_funds": 300,
    "recruit_threshold": 300,
    "recruit_cost": 300,
    "rider_speed": 50,
    "order_fee": 100,
    "fuel_divisor": 20,
    "load_penalty": 200,
    "state_file": "dispatch_state.json",
}


def load_config(path):
    """Load system parameters from a JSON file.

    Missing or invalid files fall back to the defaults, with a logged message.

    Args:
        path: Path of the JSON configuration file, or None for defaults.

    Returns:
        Dictionary of configuration parameters.
    """
    config = dict(DEFAULT_CONFIG)
    if not path:
        return config
    if not os.path.exists(path):
        logger.warning("Config file %s not found; using defaults", path)
        return config
    try:
        with open(path, "r", encoding="utf-8") as handle:
            data = json.load(handle)
    except (OSError, json.JSONDecodeError) as exc:
        logger.error("Could not read config %s: %s", path, exc)
        return config
    if not isinstance(data, dict):
        logger.error("Config %s must contain a JSON object", path)
        return config
    for key, value in data.items():
        if key in DEFAULT_CONFIG:
            config[key] = value
        else:
            logger.warning("Ignoring unknown config key '%s'", key)
    return config


def init_system(config_path=None):
    """Initialise all global state for a fresh simulation.

    Sets funds, rider list (empty), rider ID counter (0), running state
    (True), tick (0), the 8x8 grid and the order manager.

    Args:
        config_path: Optional configuration file. If None and
            ``config.json`` exists in the working directory it is used.
    """
    if config_path is None and os.path.exists(DEFAULT_CONFIG_FILE):
        config_path = DEFAULT_CONFIG_FILE
    config = load_config(config_path)

    globalvar._init()
    globalvar.set_value("config", config)
    globalvar.set_value("funds", int(config["initial_funds"]))
    globalvar.set_value("rider_id_counter", 0)
    globalvar.set_value("is_running", True)
    globalvar.set_value("current_tick", 0)
    globalvar.set_value("riders", [])
    globalvar.set_value("grid", Grid())
    globalvar.set_value("order_manager", OrderManager())
    globalvar.set_value("order_id_counter", 0)
    logger.info("System initialised")


class SystemManager:
    """Facade over the global system state.

    All state lives in ``globalvar``; this class provides typed access and
    the simulation operations (ticks, recruitment, persistence).
    """

    def __init__(self):
        """Ensure the system has been initialised."""
        if globalvar.get_value("order_manager") is None:
            init_system()

    @property
    def funds(self):
        """System fund balance (integer, may be negative)."""
        return int(globalvar.get_value("funds") or 0)

    @funds.setter
    def funds(self, value):
        globalvar.set_value("funds", int(value))

    @property
    def rider_id_counter(self):
        """Last issued rider ID."""
        return int(globalvar.get_value("rider_id_counter") or 0)

    @rider_id_counter.setter
    def rider_id_counter(self, value):
        globalvar.set_value("rider_id_counter", int(value))

    @property
    def is_running(self):
        """Whether the main loop should keep running."""
        return bool(globalvar.get_value("is_running"))

    @is_running.setter
    def is_running(self, value):
        globalvar.set_value("is_running", bool(value))

    @property
    def current_tick(self):
        """Current simulated time."""
        return int(globalvar.get_value("current_tick") or 0)

    @current_tick.setter
    def current_tick(self, value):
        globalvar.set_value("current_tick", int(value))

    @property
    def riders(self):
        """Dynamic list of riders."""
        riders = globalvar.get_value("riders")
        if riders is None:
            riders = []
            globalvar.set_value("riders", riders)
        return riders

    @property
    def order_manager(self):
        """The OrderManager instance."""
        return globalvar.get_value("order_manager")

    @property
    def grid(self):
        """The 8x8 city grid."""
        return globalvar.get_value("grid")

    @property
    def config(self):
        """Configuration dictionary."""
        return globalvar.get_value("config") or {}

    def create_rider(self):
        """Create a new idle rider with an auto-incremented ID.

        Returns:
            The newly created Rider.
        """
        self.rider_id_counter = self.rider_id_counter + 1
        rider = Rider(self.rider_id_counter)
        self.riders.append(rider)
        logger.info("Rider %s recruited", rider.rider_id)
        return rider

    def check_recruitment(self):
        """Recruit a rider when funds reach the recruitment threshold.

        Recruitment consumes ``recruit_cost`` from the funds.

        Returns:
            True if a new rider was created, else False.
        """
        threshold = int(self.config.get("recruit_threshold", 300))
        if self.funds >= threshold:
            self.funds = self.funds - int(self.config.get("recruit_cost", 300))
            self.create_rider()
            return True
        return False

    def tick(self):
        """Advance the simulation by one tick.

        Moves every rider, recruits riders when funds allow, assigns pending
        orders and verifies state consistency.

        Returns:
            Number of orders delivered during this tick.
        """
        if not self.is_running:
            return 0
        self.current_tick = self.current_tick + 1
        completed = 0
        for rider in list(self.riders):
            try:
                if rider.move():
                    completed += 1
            except Exception:  # pragma: no cover - defensive recovery
                logger.exception("Error moving rider %s", rider.rider_id)
                rider.recover()
        self.check_recruitment()
        self.order_manager.assign_pending()
        for issue in self.verify_consistency():
            logger.warning("Consistency issue: %s", issue)
        return completed

    def verify_consistency(self):
        """Check internal invariants of riders and orders.

        Returns:
            List of human readable issue descriptions (empty if healthy).
        """
        issues = []
        seen_ids = set()
        for rider in self.riders:
            if rider.rider_id in seen_ids:
                issues.append(f"duplicate rider id {rider.rider_id}")
            seen_ids.add(rider.rider_id)
            if rider.state != IDLE and not rider.orders:
                issues.append(f"rider {rider.rider_id} is busy without orders")
            if not (0 <= rider.x <= MAP_SIZE and 0 <= rider.y <= MAP_SIZE):
                issues.append(f"rider {rider.rider_id} is outside the map")
            for order in rider.orders:
                if order.rider_id != rider.rider_id:
                    issues.append(
                        f"order {order.id} is held by rider {rider.rider_id} "
                        f"but assigned to {order.rider_id}"
                    )
                if order.status == "completed":
                    issues.append(f"completed order {order.id} still held by rider")
        return issues

    def to_state_dict(self):
        """Return the full simulation state as a JSON-serialisable dict."""
        return {
            "config": dict(self.config),
            "funds": self.funds,
            "rider_id_counter": self.rider_id_counter,
            "current_tick": self.current_tick,
            "is_running": self.is_running,
            "riders": [rider.to_dict() for rider in self.riders],
            "orders": [order.to_dict() for order in self.order_manager.orders],
        }

    def save_state(self, path=None):
        """Write the simulation state to a JSON file atomically.

        Args:
            path: Destination file; defaults to ``state_file`` from config.

        Returns:
            The path that was written.

        Raises:
            OSError: If the file cannot be written.
        """
        path = path or self.config.get("state_file", DEFAULT_CONFIG["state_file"])
        temp_path = path + ".tmp"
        with open(temp_path, "w", encoding="utf-8") as handle:
            json.dump(self.to_state_dict(), handle, indent=2)
        os.replace(temp_path, path)
        logger.info("State saved to %s", path)
        return path

    def shutdown(self):
        """Stop the main loop and attempt to persist the state."""
        self.is_running = False
        try:
            self.save_state()
        except OSError as exc:
            logger.error("Could not save state on shutdown: %s", exc)
