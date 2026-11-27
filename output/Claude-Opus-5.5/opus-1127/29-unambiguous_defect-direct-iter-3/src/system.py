"""System initialisation and resource management."""

import json
import logging

import globalvar
from config import load_config, get_config_value
from rider import Rider, IDLE

logger = logging.getLogger("dispatch.system")


def init_system(config_path=None):
    """Initialise all global system parameters.

    Returns a :class:`SystemManager` bound to the global state.
    """
    cfg = load_config(config_path)
    globalvar.set_value("config", cfg)
    globalvar.set_value("funds", int(cfg["initial_funds"]))
    globalvar.set_value("riders", [])
    globalvar.set_value("rider_id_counter", 0)
    globalvar.set_value("running", True)
    globalvar.set_value("time", 0)
    globalvar.set_value("orders", [])
    globalvar.set_value("order_counter", 0)
    logger.info("System initialised with funds %s", cfg["initial_funds"])
    return SystemManager()


def _ensure_initialised():
    if globalvar.get_value("riders") is None:
        init_system()


def can_recruit():
    """True if funds and rider limit allow a new recruit."""
    _ensure_initialised()
    funds = globalvar.get_value("funds", 0)
    riders = globalvar.get_value("riders")
    return (funds >= get_config_value("rider_cost")
            and len(riders) < get_config_value("max_riders"))


def recruit_rider(force=False):
    """Recruit a new rider, deducting the cost from funds.

    Returns the new Rider, or None if not allowed (unless ``force``).
    """
    _ensure_initialised()
    if not force and not can_recruit():
        return None
    counter = (globalvar.get_value("rider_id_counter", 0) or 0) + 1
    globalvar.set_value("rider_id_counter", counter)
    globalvar.set_value("funds", globalvar.get_value("funds", 0)
                        - get_config_value("rider_cost"))
    rider = Rider(counter)
    globalvar.get_value("riders").append(rider)
    logger.info("Recruited rider %s", counter)
    return rider


class SystemManager:
    """Facade over the global system state."""

    @property
    def funds(self):
        return globalvar.get_value("funds", 0)

    @property
    def riders(self):
        _ensure_initialised()
        return globalvar.get_value("riders")

    @property
    def orders(self):
        orders = globalvar.get_value("orders")
        if orders is None:
            orders = []
            globalvar.set_value("orders", orders)
        return orders

    @property
    def time(self):
        return globalvar.get_value("time", 0) or 0

    @property
    def running(self):
        return bool(globalvar.get_value("running", False))

    def stop(self):
        """Stop the main loop."""
        globalvar.set_value("running", False)

    def can_recruit(self):
        return can_recruit()

    def recruit_rider(self, force=False):
        return recruit_rider(force)

    def get_rider(self, rider_id):
        for r in self.riders:
            if r.rider_id == rider_id:
                return r
        return None

    def tick(self, n=1):
        """Advance the simulation by ``n`` ticks."""
        for _ in range(max(0, int(n))):
            globalvar.set_value("time", self.time + 1)
            for rider in list(self.riders):
                try:
                    rider.move()
                except Exception as exc:  # pragma: no cover - recovery
                    logger.error("Rider %s failed to move: %s",
                                 rider.rider_id, exc)
                    self._recover_rider(rider)

    @staticmethod
    def _recover_rider(rider):
        rider.path = []
        if rider.current_order is not None and \
                rider.current_order.status != "completed":
            rider.current_order.status = "assigned"
        rider.current_order = None
        rider.state = IDLE

    def check_consistency(self):
        """Repair obvious inconsistencies; return a list of issues fixed."""
        issues = []
        if not isinstance(globalvar.get_value("funds"), int):
            try:
                globalvar.set_value("funds", int(globalvar.get_value("funds")))
            except (TypeError, ValueError):
                globalvar.set_value("funds", 0)
            issues.append("funds type repaired")
        seen = set()
        for rider in self.riders:
            if rider.rider_id in seen:
                issues.append("duplicate rider id %s" % rider.rider_id)
            seen.add(rider.rider_id)
            if rider.state not in (0, 1, 2):
                self._recover_rider(rider)
                issues.append("rider %s invalid state" % rider.rider_id)
            elif rider.state != IDLE and rider.current_order is None:
                self._recover_rider(rider)
                issues.append("rider %s busy without order" % rider.rider_id)
            rider.x = max(0, min(800, rider.x))
            rider.y = max(0, min(800, rider.y))
        return issues

    def to_dict(self):
        return {
            "system": dict(globalvar.get_value("config") or {}),
            "funds": self.funds,
            "time": self.time,
            "rider_id_counter": globalvar.get_value("rider_id_counter", 0),
            "riders": [r.to_dict() for r in self.riders],
            "orders": [o.to_dict() for o in self.orders],
        }

    def save_state(self, path):
        """Persist parameters, riders and order history as JSON."""
        with open(path, "w", encoding="utf-8") as fh:
            json.dump(self.to_dict(), fh, indent=2)
        return path
