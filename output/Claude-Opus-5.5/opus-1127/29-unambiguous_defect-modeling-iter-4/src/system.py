"""System initialisation and the SystemManager core class."""

import json
import logging

import globalvar
from config import DEFAULT_CONFIG
from rider import Rider

logger = logging.getLogger(__name__)


def _ensure_defaults():
    """Fill in any missing global values with defaults."""
    cfg = globalvar.get_value("config")
    if not isinstance(cfg, dict):
        cfg = dict(DEFAULT_CONFIG)
        globalvar.set_value("config", cfg)
    defaults = {
        "funds": int(cfg.get("initial_funds", DEFAULT_CONFIG["initial_funds"])),
        "riders": [],
        "rider_id_counter": 0,
        "running": True,
        "current_time": 0,
        "orders": [],
        "order_id_counter": 0,
        "recruitment_cost": int(cfg.get("recruitment_cost",
                                        DEFAULT_CONFIG["recruitment_cost"])),
    }
    for key, value in defaults.items():
        if globalvar.get_value(key) is None:
            globalvar.set_value(key, value)


def init_system(config=None):
    """Initialise all global system parameters.

    Args:
        config: Optional dict overriding default configuration values.

    Returns:
        A :class:`SystemManager` bound to the freshly initialised state.
    """
    globalvar._init()
    cfg = dict(DEFAULT_CONFIG)
    if isinstance(config, dict):
        cfg.update(config)
    globalvar.set_value("config", cfg)
    globalvar.set_value("funds", int(cfg["initial_funds"]))
    globalvar.set_value("riders", [])
    globalvar.set_value("rider_id_counter", 0)
    globalvar.set_value("running", True)
    globalvar.set_value("current_time", 0)
    globalvar.set_value("orders", [])
    globalvar.set_value("order_id_counter", 0)
    globalvar.set_value("recruitment_cost", int(cfg["recruitment_cost"]))
    logger.info("System initialised with funds=%s", cfg["initial_funds"])
    return SystemManager()


class SystemManager:
    """Manages funds, riders, simulated time and system state."""

    def __init__(self):
        _ensure_defaults()

    # -------------------------------------------------------------- properties
    @property
    def config(self):
        """Effective configuration dict."""
        return globalvar.get_value("config")

    @property
    def funds(self):
        """Current fund balance (may be negative)."""
        return int(globalvar.get_value("funds", 0) or 0)

    @funds.setter
    def funds(self, value):
        globalvar.set_value("funds", int(value))

    @property
    def riders(self):
        """List of all riders."""
        riders = globalvar.get_value("riders")
        if not isinstance(riders, list):
            riders = []
            globalvar.set_value("riders", riders)
        return riders

    @property
    def orders(self):
        """List of all orders ever created."""
        orders = globalvar.get_value("orders")
        if not isinstance(orders, list):
            orders = []
            globalvar.set_value("orders", orders)
        return orders

    @property
    def rider_id_counter(self):
        """Rider id counter."""
        return int(globalvar.get_value("rider_id_counter", 0) or 0)

    @property
    def running(self):
        """Main loop running flag."""
        return bool(globalvar.get_value("running", True))

    @running.setter
    def running(self, value):
        globalvar.set_value("running", bool(value))

    @property
    def current_time(self):
        """Current simulated time (ticks)."""
        return int(globalvar.get_value("current_time", 0) or 0)

    @property
    def recruitment_cost(self):
        """Cost of recruiting a rider."""
        return int(globalvar.get_value("recruitment_cost",
                                       DEFAULT_CONFIG["recruitment_cost"]))

    @property
    def max_riders(self):
        """Maximum number of riders."""
        return int(self.config.get("max_riders", DEFAULT_CONFIG["max_riders"]))

    # ----------------------------------------------------------------- riders
    def can_recruit(self):
        """True if funds allow recruiting another rider and the cap is not reached."""
        return (self.funds >= self.recruitment_cost
                and len(self.riders) < self.max_riders)

    def recruit_rider(self, force=False):
        """Recruit a new rider, deducting the recruitment cost.

        Args:
            force: Recruit even if funds are insufficient (funds go negative).

        Returns:
            The new :class:`Rider` or None if recruitment was not possible.
        """
        if not force and not self.can_recruit():
            return None
        riders = self.riders
        max_existing = max((r.rider_id for r in riders), default=0)
        new_id = max(self.rider_id_counter, max_existing) + 1
        globalvar.set_value("rider_id_counter", new_id)
        rider = Rider(new_id)
        self.funds = self.funds - self.recruitment_cost
        riders.append(rider)
        logger.info("Recruited rider %s; funds now %s", new_id, self.funds)
        return rider

    def get_rider(self, rider_id):
        """Return the rider with ``rider_id`` or None."""
        for rider in self.riders:
            if rider.rider_id == rider_id:
                return rider
        return None

    # -------------------------------------------------------------- simulation
    def tick(self, count=1):
        """Advance the simulation by ``count`` ticks.

        Returns:
            List of ``(rider_id, log_entry)`` tuples for events that occurred.
        """
        events = []
        for _ in range(max(0, int(count))):
            globalvar.set_value("current_time", self.current_time + 1)
            for rider in list(self.riders):
                before = len(rider.log)
                try:
                    rider.move()
                except Exception as exc:  # pylint: disable=broad-except
                    logger.error("Rider %s failed to move: %s", rider.rider_id, exc)
                    rider.reset_route()
                    self.check_consistency()
                for entry in rider.log[before:]:
                    events.append((rider.rider_id, entry))
        return events

    def has_pending_work(self):
        """True if any rider still has orders to deliver."""
        return any(r.active_orders() for r in self.riders)

    def check_consistency(self):
        """Detect and repair inconsistent state. Returns list of issues fixed."""
        issues = []
        for rider in self.riders:
            if rider.state not in (0, 1, 2):
                issues.append(f"rider {rider.rider_id} invalid state {rider.state}")
                rider.state = 0
                rider.reset_route()
            if not rider.active_orders() and rider.state != 0:
                issues.append(f"rider {rider.rider_id} busy without orders")
                rider.state = 0
                rider.reset_route()
            cx = max(0, min(800, int(rider.x)))
            cy = max(0, min(800, int(rider.y)))
            if (cx, cy) != (rider.x, rider.y):
                issues.append(f"rider {rider.rider_id} out of bounds")
                rider.x, rider.y = cx, cy
                rider.reset_route()
        if issues:
            logger.warning("Consistency issues fixed: %s", issues)
        return issues

    # ------------------------------------------------------------- persistence
    def to_dict(self):
        """Serialise the full system state."""
        return {
            "config": self.config,
            "funds": self.funds,
            "current_time": self.current_time,
            "rider_id_counter": self.rider_id_counter,
            "riders": [r.to_dict() for r in self.riders],
            "orders": [o.to_dict() for o in self.orders],
        }

    def save_state(self, path):
        """Write the system state to ``path`` as JSON. Returns True on success."""
        try:
            with open(path, "w", encoding="utf-8") as fh:
                json.dump(self.to_dict(), fh, indent=2)
            return True
        except (OSError, TypeError, ValueError) as exc:
            logger.error("Failed to save state to %s: %s", path, exc)
            return False
