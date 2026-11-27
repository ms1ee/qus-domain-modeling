"""System initialization and the SystemManager core class."""

import json
import logging

import globalvar
from config import DEFAULT_CONFIG
from rider import IDLE, Rider

logger = logging.getLogger(__name__)


def init_system(config=None):
    """Initialize all core system parameters in the global registry."""
    cfg = dict(DEFAULT_CONFIG)
    if config:
        cfg.update(config)
    globalvar.set_value("config", cfg)
    globalvar.set_value("funds", int(cfg["initial_funds"]))
    globalvar.set_value("riders", [])
    globalvar.set_value("rider_id_counter", 0)
    globalvar.set_value("running", True)
    globalvar.set_value("time", 0)
    globalvar.set_value("orders", [])
    globalvar.set_value("pending_orders", [])
    globalvar.set_value("order_id_counter", 0)
    logger.debug("System initialized with config %s", cfg)


def _ensure_initialized():
    """Fill in any missing global keys with default values."""
    defaults = {
        "config": dict(DEFAULT_CONFIG),
        "funds": DEFAULT_CONFIG["initial_funds"],
        "riders": [],
        "rider_id_counter": 0,
        "running": True,
        "time": 0,
        "orders": [],
        "pending_orders": [],
        "order_id_counter": 0,
    }
    for key, value in defaults.items():
        if globalvar.get_value(key) is None:
            globalvar.set_value(key, value)
    riders = globalvar.get_value("riders")
    if riders:
        counter = globalvar.get_value("rider_id_counter") or 0
        max_id = max(r.rider_id for r in riders)
        if max_id > counter:
            globalvar.set_value("rider_id_counter", max_id)


class SystemManager:
    """Manages funds, riders, simulated time and system state."""

    def __init__(self):
        _ensure_initialized()

    @property
    def config(self):
        return globalvar.get_value("config")

    @property
    def funds(self):
        return globalvar.get_value("funds")

    @property
    def riders(self):
        return globalvar.get_value("riders")

    @property
    def time(self):
        return globalvar.get_value("time")

    @property
    def running(self):
        return globalvar.get_value("running")

    def stop(self):
        """Stop the main loop."""
        globalvar.set_value("running", False)

    def idle_riders(self):
        """Riders that are idle and have no queued orders."""
        return [r for r in self.riders if r.state == IDLE and not r.orders]

    def can_recruit(self):
        """True when funds allow recruiting and the rider cap is not hit."""
        cfg = self.config
        return (self.funds >= cfg["rider_cost"]
                and len(self.riders) < cfg["max_riders"])

    def recruit_rider(self):
        """Recruit a new rider if possible; returns it or None."""
        if not self.can_recruit():
            return None
        counter = (globalvar.get_value("rider_id_counter") or 0) + 1
        globalvar.set_value("rider_id_counter", counter)
        rider = Rider(counter)
        globalvar.set_value("funds", self.funds - self.config["rider_cost"])
        self.riders.append(rider)
        logger.info("Recruited rider %s", counter)
        return rider

    def check_consistency(self):
        """Repair inconsistent rider states."""
        for rider in self.riders:
            if rider.state != IDLE and not rider.orders:
                logger.warning("Rider %s busy without orders; reset",
                               rider.rider_id)
                rider.state = IDLE
                rider.path = []
                rider.special_case = False
            if rider.state not in (0, 1, 2):
                rider.state = IDLE
                rider.path = []

    def tick(self, count=1):
        """Advance the simulation by ``count`` ticks."""
        from order import OrderManager
        manager = OrderManager(self)
        for _ in range(max(0, int(count))):
            globalvar.set_value("time", self.time + 1)
            manager.process_pending()
            for rider in list(self.riders):
                try:
                    rider.move()
                except Exception as exc:  # error recovery
                    logger.error("Rider %s failed to move: %s",
                                 rider.rider_id, exc)
                    rider.path = []
            self.check_consistency()

    def snapshot(self):
        """Serializable state of the whole system."""
        orders = globalvar.get_value("orders") or []
        return {
            "config": self.config,
            "funds": self.funds,
            "time": self.time,
            "rider_id_counter": globalvar.get_value("rider_id_counter"),
            "riders": [r.to_dict() for r in self.riders],
            "orders": [o.to_dict() for o in orders],
        }

    def save_state(self, path=None):
        """Write the system state to a JSON file. Returns the path or None."""
        path = path or self.config.get("state_file", "dispatch_state.json")
        try:
            with open(path, "w", encoding="utf-8") as fh:
                json.dump(self.snapshot(), fh, indent=2)
            return path
        except OSError as exc:
            logger.error("Could not save state: %s", exc)
            return None
