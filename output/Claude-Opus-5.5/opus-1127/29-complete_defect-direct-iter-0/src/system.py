"""System initialisation and the SystemManager core class."""

import json
import logging
import os

import globalvar
from order import OrderManager
from order_model import Order
from rider import Rider

logger = logging.getLogger(__name__)

DEFAULT_CONFIG = {
    "initial_funds": 300,
    "recruit_threshold": 300,
    "rider_cost": 300,
    "order_income": 100,
    "rider_speed": 50,
    "spawn_x": 400,
    "spawn_y": 400,
    "max_riders": 50,
    "state_file": "dispatch_state.json",
}


def load_config(path=None):
    """Load a JSON configuration file merged over the defaults."""
    cfg = dict(DEFAULT_CONFIG)
    if path and os.path.exists(path):
        try:
            with open(path, "r", encoding="utf-8") as fh:
                data = json.load(fh)
            if isinstance(data, dict):
                cfg.update({k: v for k, v in data.items() if k in cfg})
        except (OSError, ValueError) as exc:
            logger.warning("Failed to load config %s: %s", path, exc)
    return cfg


def init_system(config=None):
    """Initialise all global system parameters."""
    globalvar._init()
    cfg = dict(DEFAULT_CONFIG)
    if config:
        cfg.update(config)
    globalvar.set_value("config", cfg)
    globalvar.set_value("funds", int(cfg["initial_funds"]))
    globalvar.set_value("riders", [])
    globalvar.set_value("rider_id_counter", 0)
    globalvar.set_value("running", True)
    globalvar.set_value("orders", [])
    globalvar.set_value("time", 0)
    Order.reset_counter()


class SystemManager:
    """Manages funds, riders, simulated time and overall system state."""

    def __init__(self, config=None, config_path=None):
        cfg = load_config(config_path)
        if config:
            cfg.update(config)
        init_system(cfg)
        self.order_manager = OrderManager()

    # properties -------------------------------------------------------
    @property
    def config(self):
        return globalvar.get_value("config")

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
        """Stop the main loop."""
        globalvar.set_value("running", False)

    # riders -----------------------------------------------------------
    def create_rider(self):
        """Create a rider with the next id and add it to the list."""
        counter = globalvar.get_value("rider_id_counter", 0) + 1
        globalvar.set_value("rider_id_counter", counter)
        rider = Rider(counter)
        self.riders.append(rider)
        logger.info("Recruited rider %d", counter)
        return rider

    def remove_rider(self, rider_id):
        """Remove an idle rider; returns True on success."""
        for r in self.riders:
            if r.rider_id == rider_id and r.is_available():
                self.riders.remove(r)
                return True
        return False

    def get_rider(self, rider_id):
        """Find rider by id."""
        for r in self.riders:
            if r.rider_id == rider_id:
                return r
        return None

    def recruit_if_possible(self):
        """Recruit a rider when funds >= threshold; returns rider or None."""
        cfg = self.config
        if (self.funds >= cfg["recruit_threshold"]
                and len(self.riders) < cfg["max_riders"]):
            globalvar.set_value("funds", self.funds - cfg["rider_cost"])
            return self.create_rider()
        return None

    # simulation -------------------------------------------------------
    def tick(self, n=1):
        """Advance simulated time by ``n`` ticks."""
        for _ in range(max(0, int(n))):
            globalvar.set_value("time", self.time + 1)
            try:
                self.recruit_if_possible() if self.order_manager \
                    .pending_orders() else None
                self.order_manager.assign_pending()
                for rider in list(self.riders):
                    rider.move()
                self.check_consistency()
            except Exception as exc:  # error recovery
                logger.exception("Error during tick: %s", exc)
                self.check_consistency()

    def check_consistency(self):
        """Verify and repair system state; returns list of fixes made."""
        fixes = []
        rider_ids = {r.rider_id for r in self.riders}
        for order in self.order_manager.all_orders():
            if order.status == "completed":
                continue
            if order.rider_id is not None and order.rider_id not in rider_ids:
                order.rider_id = None
                order.status = "pending"
                fixes.append("order %d orphaned -> pending" % order.id)
            elif order.rider_id is not None:
                rider = self.get_rider(order.rider_id)
                if order not in rider.orders:
                    rider.orders.append(order)
                    fixes.append("order %d re-queued" % order.id)
        for r in self.riders:
            if r.state not in (0, 1, 2):
                r.state = 0
                r.current_order = None
                fixes.append("rider %d state reset" % r.rider_id)
            if r.state != 0 and r.current_order is None:
                r.state = 0
                fixes.append("rider %d state reset" % r.rider_id)
        for f in fixes:
            logger.warning("Consistency fix: %s", f)
        return fixes

    # persistence ------------------------------------------------------
    def to_dict(self):
        """Serialisable system snapshot."""
        return {
            "config": self.config,
            "funds": self.funds,
            "time": self.time,
            "rider_id_counter": globalvar.get_value("rider_id_counter", 0),
            "riders": [r.to_dict() for r in self.riders],
            "orders": [o.to_dict() for o in self.order_manager.all_orders()],
        }

    def save_state(self, path=None):
        """Write the snapshot to a JSON file; returns the path or None."""
        path = path or self.config.get("state_file", "dispatch_state.json")
        try:
            with open(path, "w", encoding="utf-8") as fh:
                json.dump(self.to_dict(), fh, indent=2)
            return path
        except OSError as exc:
            logger.error("Could not save state: %s", exc)
            return None
