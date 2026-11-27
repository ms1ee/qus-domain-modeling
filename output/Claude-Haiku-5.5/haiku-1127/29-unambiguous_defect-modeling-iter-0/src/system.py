"""System state management: funds, riders, ticks, configuration and persistence."""

import json
import logging
import os

import globalvar
from order import OrderManager
from rider import Rider

logger = logging.getLogger("dispatch.system")

DEFAULT_CONFIG = {
    "initial_funds": 5000,
    "recruitment_cost": 500,
    "max_riders": 20,
    "delivery_fee": 80,
    "operating_cost_per_rider_tick": 1,
    "state_file": "dispatch_state.json",
}


def load_config(path=None):
    """Load system parameters from an optional JSON file.

    Unknown keys are ignored; missing keys keep their defaults. Numeric keys
    are validated and fall back to defaults when invalid.

    Args:
        path: Path to a JSON configuration file, or None for defaults only.

    Returns:
        dict: Effective configuration.
    """
    config = dict(DEFAULT_CONFIG)
    if path and os.path.exists(path):
        try:
            with open(path, encoding="utf-8") as handle:
                data = json.load(handle)
        except (OSError, json.JSONDecodeError) as exc:
            logger.warning("could not read config %s: %s", path, exc)
            return config
        if isinstance(data, dict):
            for key in DEFAULT_CONFIG:
                if key in data:
                    config[key] = data[key]
    for key in ("initial_funds", "recruitment_cost", "max_riders",
                "delivery_fee", "operating_cost_per_rider_tick"):
        try:
            config[key] = int(config[key])
        except (TypeError, ValueError):
            logger.warning("invalid config value for %s; using default", key)
            config[key] = DEFAULT_CONFIG[key]
    return config


class SystemManager:
    """Core simulation controller.

    Attributes:
        funds (int): System funds; may become negative.
        rider_id_counter (int): Last issued rider id.
        is_running (bool): Main-loop control flag.
        current_tick (int): Simulated time.
        recruitment_cost (int): Cost deducted per recruited rider.
        max_riders (int): Upper bound on rider count.
        delivery_fee (int): Income per completed order.
        operating_cost_per_rider_tick (int): Cost per rider per tick.
        state_file (str): Default path for saving state.
        order_manager (OrderManager): Owns all orders.
    """

    def __init__(self, config=None):
        """Create the system manager from a configuration dictionary.

        Args:
            config: Optional dictionary overriding DEFAULT_CONFIG values.
        """
        cfg = dict(DEFAULT_CONFIG)
        cfg.update(config or {})
        self.funds = int(cfg["initial_funds"])
        self.recruitment_cost = int(cfg["recruitment_cost"])
        self.max_riders = int(cfg["max_riders"])
        self.delivery_fee = int(cfg["delivery_fee"])
        self.operating_cost_per_rider_tick = int(cfg["operating_cost_per_rider_tick"])
        self.state_file = str(cfg["state_file"])
        self.rider_id_counter = 0
        self.is_running = True
        self.current_tick = 0
        self.order_manager = OrderManager()
        globalvar.set_value("current_tick", 0)

    @property
    def riders(self):
        """Return the shared rider list stored in the global variable store."""
        riders = globalvar.get_value("riders")
        if riders is None:
            riders = []
            globalvar.set_value("riders", riders)
        return riders

    def has_idle_rider(self):
        """Return True if at least one rider is idle."""
        return any(rider.state == 0 for rider in self.riders)

    def recruit_rider(self):
        """Recruit a new rider if funds and the rider cap allow it.

        Returns:
            Rider | None: The new rider, or None if recruitment is not possible.
        """
        if len(self.riders) >= self.max_riders:
            logger.info("rider cap %d reached", self.max_riders)
            return None
        if self.funds < self.recruitment_cost:
            logger.info("insufficient funds (%d) to recruit", self.funds)
            return None
        self.funds -= self.recruitment_cost
        self.rider_id_counter += 1
        rider = Rider(self.rider_id_counter)
        self.riders.append(rider)
        logger.info("recruited rider #%d", rider.rider_id)
        return rider

    def advance_tick(self, steps=1):
        """Advance the simulation by ``steps`` ticks.

        Each tick moves every rider, settles completed orders (delivery fees)
        and charges operating costs.

        Args:
            steps: Number of ticks to simulate.
        """
        for _ in range(int(steps)):
            self.current_tick += 1
            globalvar.set_value("current_tick", self.current_tick)
            for rider in list(self.riders):
                try:
                    rider.move()
                except Exception:  # error recovery: keep the simulation running
                    logger.exception("rider #%d failed during move; repairing", rider.rider_id)
                    rider.repair()
            for _order in self.order_manager.settle_completed():
                self.funds += self.delivery_fee
            self.funds -= self.operating_cost_per_rider_tick * len(self.riders)

    def check_consistency(self):
        """Check and repair system state.

        Returns:
            list[str]: Human-readable descriptions of issues found (empty if OK).
        """
        issues = []
        ids = [rider.rider_id for rider in self.riders]
        if len(ids) != len(set(ids)):
            issues.append("duplicate rider identifiers detected")
        if len(self.riders) > self.max_riders:
            issues.append("rider count exceeds configured maximum")
        for rider in self.riders:
            for problem in rider.repair():
                issues.append(f"rider #{rider.rider_id}: {problem}")
        for order in self.order_manager.active_orders():
            if order.rider_id not in ids:
                issues.append(f"order #{order.id} references missing rider #{order.rider_id}")
        return issues

    def to_dict(self):
        """Return a JSON-serialisable snapshot of the whole system."""
        return {
            "funds": self.funds,
            "current_tick": self.current_tick,
            "rider_id_counter": self.rider_id_counter,
            "riders": [rider.to_dict() for rider in self.riders],
            "orders": [order.to_dict() for order in self.order_manager.orders],
        }

    def save_state(self, path=None):
        """Write the system snapshot to a JSON file.

        Args:
            path: Destination path; defaults to ``self.state_file``.

        Returns:
            str: The path that was written.

        Raises:
            OSError: If the file cannot be written.
        """
        target = path or self.state_file
        tmp_path = target + ".tmp"
        with open(tmp_path, "w", encoding="utf-8") as handle:
            json.dump(self.to_dict(), handle, indent=2)
        os.replace(tmp_path, target)
        logger.info("state saved to %s", target)
        return target


def init_system(config=None):
    """Initialise global variables and create the system manager.

    Args:
        config: Optional configuration dictionary (see ``load_config``).

    Returns:
        SystemManager: The initialised system manager.
    """
    globalvar._init()
    return SystemManager(config)
