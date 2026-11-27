"""System initialisation and the SystemManager core class."""

import json
import logging
import os

import globalvar
from order import OrderManager, hire_rider

DEFAULT_FUNDS = 1000
CONFIG_FILE = "config.json"
STATE_FILE = "dispatch_state.json"

logger = logging.getLogger("dispatch")


def _load_config(path=CONFIG_FILE):
    if not path or not os.path.exists(path):
        return {}
    try:
        with open(path, "r", encoding="utf-8") as fh:
            data = json.load(fh)
        return data if isinstance(data, dict) else {}
    except (OSError, ValueError) as exc:
        logger.warning("Could not read config %s: %s", path, exc)
        return {}


def init_system(config_path=None):
    """Initialise all global system parameters and return a SystemManager."""
    globalvar._init()
    cfg = _load_config(config_path) if config_path else {}
    funds = cfg.get("funds", DEFAULT_FUNDS)
    if not isinstance(funds, int):
        funds = DEFAULT_FUNDS
    globalvar.set_value("funds", funds)
    globalvar.set_value("riders", [])
    globalvar.set_value("rider_id_counter", 0)
    globalvar.set_value("running", True)
    globalvar.set_value("time", 0)
    globalvar.set_value("orders", [])
    return SystemManager()


class SystemManager:
    """Manages funds, riders, simulated time and persistence."""

    def __init__(self):
        if globalvar.get_value("riders") is None:
            globalvar.set_value("riders", [])
        if globalvar.get_value("funds") is None:
            globalvar.set_value("funds", DEFAULT_FUNDS)
        if globalvar.get_value("time") is None:
            globalvar.set_value("time", 0)
        if globalvar.get_value("running") is None:
            globalvar.set_value("running", True)
        self.order_manager = OrderManager()

    @property
    def funds(self):
        return globalvar.get_value("funds", 0)

    @property
    def riders(self):
        return globalvar.get_value("riders", [])

    @property
    def time(self):
        return globalvar.get_value("time", 0)

    @property
    def running(self):
        return globalvar.get_value("running", False)

    def stop(self):
        globalvar.set_value("running", False)

    def hire_rider(self):
        return hire_rider()

    def tick(self, n=1):
        """Advance the simulation by ``n`` ticks."""
        for _ in range(max(0, int(n))):
            globalvar.set_value("time", self.time + 1)
            for rider in list(self.riders):
                try:
                    rider.move()
                except Exception as exc:  # recover from a faulty rider
                    logger.exception("Rider %s failed to move: %s",
                                     rider.rider_id, exc)
                    rider.current_order = None
            for order in self.order_manager.pending_orders():
                self.order_manager.assign(order)

    def all_done(self):
        return all(o.status == "completed" for o in self.order_manager.all_orders())

    def consistency_check(self):
        """Return a list of detected inconsistencies (empty if fine)."""
        problems = []
        ids = [r.rider_id for r in self.riders]
        if len(ids) != len(set(ids)):
            problems.append("duplicate rider ids")
        for r in self.riders:
            if r.state not in (0, 1, 2):
                problems.append("rider %s has invalid state" % r.rider_id)
            if r.state == 0 and r.active_orders() and r.current_order is not None:
                problems.append("rider %s idle with active order" % r.rider_id)
        return problems

    def save(self, path=STATE_FILE):
        """Persist system parameters, riders and order history as JSON."""
        data = {
            "funds": self.funds,
            "time": self.time,
            "rider_id_counter": globalvar.get_value("rider_id_counter", 0),
            "riders": [r.to_dict() for r in self.riders],
            "orders": [o.to_dict() for o in self.order_manager.all_orders()],
        }
        with open(path, "w", encoding="utf-8") as fh:
            json.dump(data, fh, indent=2)
        return path
