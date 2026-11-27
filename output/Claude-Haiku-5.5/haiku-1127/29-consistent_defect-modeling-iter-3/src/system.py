"""System initialisation and the core SystemManager.

SystemManager owns the system funds, the rider list, the simulation tick,
and the order flow: order submission, automatic rider recruitment, dispatch,
and the simulation loop.
"""

import json
import logging

import globalvar
from order import OrderManager, find_best_rider_for_order
from rider import Rider, STATE_IDLE

logger = logging.getLogger(__name__)

DEFAULT_CONFIG = {
    "initial_funds": 1000,
    "recruit_threshold": 300,
    "recruit_cost": 500,
}


def _load_config(path):
    """Load system parameters from a JSON file, falling back to defaults.

    Args:
        path: Path to a JSON file, or None to use defaults only.

    Returns:
        Dictionary of configuration parameters.
    """
    config = dict(DEFAULT_CONFIG)
    if path is None:
        return config
    try:
        with open(path, "r", encoding="utf-8") as handle:
            data = json.load(handle)
    except FileNotFoundError:
        logger.warning("Config file %s not found; using defaults", path)
        return config
    except (OSError, json.JSONDecodeError) as exc:
        logger.error("Could not read config %s: %s; using defaults", path, exc)
        return config
    for key in DEFAULT_CONFIG:
        if key in data:
            try:
                config[key] = int(data[key])
            except (TypeError, ValueError):
                logger.error("Invalid value for config key %s; using default", key)
    return config


def init_system(config_path=None):
    """Initialise global variables and return a new SystemManager.

    Sets funds to the configured initial value (default 1000), an empty rider
    list, rider ID counter 0, running state True and tick 0.

    Args:
        config_path: Optional path to a JSON configuration file.

    Returns:
        A ready-to-use ``SystemManager``.
    """
    config = _load_config(config_path)
    globalvar._init()
    globalvar.set_value("config", config)
    globalvar.set_value("funds", config["initial_funds"])
    globalvar.set_value("riders", [])
    globalvar.set_value("rider_id_counter", 0)
    globalvar.set_value("is_running", True)
    globalvar.set_value("current_tick", 0)
    logger.info("System initialised with funds=%s", config["initial_funds"])
    return SystemManager()


class SystemManager:
    """Manages funds, riders, orders and the simulation clock.

    Attributes:
        config (dict): Active configuration parameters.
        order_manager (OrderManager): Order registry and assignment helper.
    """

    def __init__(self):
        """Bind to the global state initialised by ``init_system``."""
        self.config = globalvar.get_value("config") or dict(DEFAULT_CONFIG)
        self.order_manager = OrderManager()

    # ------------------------------------------------------------------
    # State accessors
    # ------------------------------------------------------------------
    @property
    def funds(self):
        """Current system funds (may be negative)."""
        return globalvar.get_value("funds", 0)

    @property
    def riders(self):
        """List of all riders."""
        return globalvar.get_value("riders")

    @property
    def current_tick(self):
        """Current simulated time."""
        return globalvar.get_value("current_tick", 0)

    @property
    def is_running(self):
        """True while the main loop should keep running."""
        return globalvar.get_value("is_running", False)

    def stop(self):
        """Request the main loop to stop."""
        globalvar.set_value("is_running", False)

    def idle_riders(self):
        """Return riders in the idle state."""
        return [rider for rider in self.riders if rider.state == STATE_IDLE]

    # ------------------------------------------------------------------
    # Recruitment and dispatch
    # ------------------------------------------------------------------
    def recruit_rider(self):
        """Create a new rider if funds allow, deducting the recruitment cost.

        Returns:
            The new ``Rider``, or None when funds are below the threshold.
        """
        threshold = self.config["recruit_threshold"]
        cost = self.config["recruit_cost"]
        if self.funds < threshold:
            return None
        globalvar.set_value("funds", self.funds - cost)
        new_id = globalvar.get_value("rider_id_counter", 0) + 1
        globalvar.set_value("rider_id_counter", new_id)
        rider = Rider(new_id)
        self.riders.append(rider)
        logger.info("Recruited rider %s (funds now %s)", new_id, self.funds)
        return rider

    def _should_recruit(self, pending_count):
        """Return True when funds allow and pending orders exceed idle riders."""
        return (
            self.funds >= self.config["recruit_threshold"]
            and pending_count > len(self.idle_riders())
        )

    def _try_dispatch(self, order):
        """Attempt to assign ``order`` to a rider, recruiting one if needed.

        Returns:
            Tuple ``(rider, new_rider)`` where ``rider`` is the assigned rider
            or None, and ``new_rider`` is True when a rider was recruited.
        """
        pending_count = len(self.order_manager.pending_orders())
        recruited = None
        if self._should_recruit(pending_count):
            recruited = self.recruit_rider()
        rider = find_best_rider_for_order(order)
        if rider is None:
            return None, recruited is not None
        self.order_manager.assign_order(order, rider)
        return rider, recruited is not None

    def submit_order(self, restaurant_xy, customer_xy):
        """Create an order from user coordinates and dispatch it.

        Args:
            restaurant_xy: ``(x, y)`` restaurant coordinates.
            customer_xy: ``(x, y)`` customer coordinates.

        Returns:
            Dictionary with keys "order" (Order), "rider" (Rider or None)
            and "new_rider" (Rider recruited for this order, or None).
        """
        order = self.order_manager.create_order(restaurant_xy, customer_xy)
        rider, recruited = self._try_dispatch(order)
        new_rider = self.riders[-1] if recruited else None
        return {"order": order, "rider": rider, "new_rider": new_rider}

    def dispatch_pending(self):
        """Retry assignment for orders that are still pending."""
        for order in self.order_manager.pending_orders():
            self._try_dispatch(order)

    # ------------------------------------------------------------------
    # Simulation loop
    # ------------------------------------------------------------------
    def tick(self):
        """Advance the simulation by one tick and move every rider."""
        globalvar.set_value("current_tick", self.current_tick + 1)
        for rider in list(self.riders):
            rider.move()
        self.dispatch_pending()

    def run_ticks(self, count):
        """Advance the simulation by ``count`` ticks."""
        for _ in range(count):
            self.tick()

    # ------------------------------------------------------------------
    # Monitoring and persistence
    # ------------------------------------------------------------------
    def check_consistency(self):
        """Verify internal state and return a list of problems (empty if OK)."""
        issues = []
        ids = [rider.rider_id for rider in self.riders]
        if len(ids) != len(set(ids)):
            issues.append("Duplicate rider IDs detected")
        for rider in self.riders:
            has_work = bool(rider.active_orders())
            if rider.state == STATE_IDLE and has_work:
                issues.append(f"Rider {rider.rider_id} is idle but has active orders")
            if rider.state != STATE_IDLE and not has_work:
                issues.append(f"Rider {rider.rider_id} is busy without active orders")
        return issues

    def snapshot(self):
        """Return a JSON-serialisable snapshot of the whole system."""
        return {
            "config": self.config,
            "funds": self.funds,
            "current_tick": self.current_tick,
            "rider_id_counter": globalvar.get_value("rider_id_counter", 0),
            "riders": [rider.to_dict() for rider in self.riders],
            "orders": [order.to_dict() for order in self.order_manager.orders],
        }

    def save_state(self, path):
        """Write the system snapshot to a JSON file.

        Args:
            path: Destination file path.

        Raises:
            OSError: If the file cannot be written.
        """
        with open(path, "w", encoding="utf-8") as handle:
            json.dump(self.snapshot(), handle, indent=2)
        logger.info("State saved to %s", path)
