"""System manager: funds, riders, time, recruitment and persistence."""

import json
import logging
import os

import globalvar
from rider import Rider, STATE_IDLE

logger = logging.getLogger(__name__)

DEFAULT_CONFIG = {
    "initial_funds": 1000,
    "recruit_cost": 500,
    "recruit_threshold": 300,
    "rider_speed": 20,
    "rider_start": [400, 400],
}


def load_config(path):
    """Load a JSON configuration file merged over the defaults."""
    cfg = dict(DEFAULT_CONFIG)
    if path and os.path.exists(path):
        try:
            with open(path, "r", encoding="utf-8") as fh:
                data = json.load(fh)
            if isinstance(data, dict):
                for key in DEFAULT_CONFIG:
                    if key in data:
                        cfg[key] = data[key]
        except (OSError, ValueError) as exc:
            logger.warning("Failed to load config %s: %s", path, exc)
    return cfg


class SystemManager:
    """Manage funds, riders, orders and simulated time."""

    def __init__(self, config=None):
        self.config = dict(DEFAULT_CONFIG)
        if config:
            self.config.update(config)

    def init(self):
        """Initialise global state."""
        globalvar._init()
        globalvar.set_value("config", self.config)
        globalvar.set_value("funds", int(self.config["initial_funds"]))
        globalvar.set_value("riders", [])
        globalvar.set_value("rider_id_counter", 0)
        globalvar.set_value("running", True)
        globalvar.set_value("orders", [])
        globalvar.set_value("time", 0)
        globalvar.set_value("system", self)

    # ------------------------------------------------------------------
    @property
    def funds(self):
        """Current system funds."""
        return globalvar.get_value("funds", 0)

    @funds.setter
    def funds(self, value):
        globalvar.set_value("funds", int(value))

    @property
    def riders(self):
        """List of riders."""
        riders = globalvar.get_value("riders")
        if riders is None:
            riders = []
            globalvar.set_value("riders", riders)
        return riders

    @property
    def orders(self):
        """List of all orders."""
        orders = globalvar.get_value("orders")
        if orders is None:
            orders = []
            globalvar.set_value("orders", orders)
        return orders

    @property
    def time(self):
        """Current simulated tick."""
        return globalvar.get_value("time", 0)

    @property
    def running(self):
        """System running flag."""
        return globalvar.get_value("running", True)

    def stop(self):
        """Stop the main loop."""
        globalvar.set_value("running", False)

    # ------------------------------------------------------------------
    def recruit_rider(self):
        """Create a new rider and deduct the recruitment cost."""
        counter = globalvar.get_value("rider_id_counter", 0) + 1
        globalvar.set_value("rider_id_counter", counter)
        rider = Rider(counter)
        self.riders.append(rider)
        self.funds = self.funds - int(self.config["recruit_cost"])
        logger.info("Recruited rider %d", counter)
        return rider

    def get_rider(self, rider_id):
        """Return the rider with the given id or None."""
        for rider in self.riders:
            if rider.rider_id == rider_id:
                return rider
        return None

    def idle_rider_count(self):
        """Number of riders that are idle with no outstanding orders."""
        return sum(1 for r in self.riders
                   if r.state == STATE_IDLE and r.current_order() is None)

    def pending_order_count(self):
        """Number of orders not yet assigned to any rider."""
        return sum(1 for o in self.orders if o.status == "pending")

    def auto_recruit(self):
        """Recruit riders while funds allow and pending > idle riders."""
        recruited = []
        threshold = int(self.config["recruit_threshold"])
        while (self.funds >= threshold
               and self.pending_order_count() > self.idle_rider_count()):
            recruited.append(self.recruit_rider())
        return recruited

    # ------------------------------------------------------------------
    def tick(self, count=1):
        """Advance the simulation by ``count`` ticks."""
        for _ in range(max(0, int(count))):
            globalvar.set_value("time", self.time + 1)
            for rider in list(self.riders):
                try:
                    rider.move()
                except Exception as exc:  # recover from rider errors
                    logger.error("Rider %s failed to move: %s",
                                 rider.rider_id, exc)
                    rider.route = []

    def check_consistency(self):
        """Repair simple inconsistencies; return list of fixes applied."""
        fixes = []
        for rider in self.riders:
            if rider.current_order() is None and rider.state != STATE_IDLE:
                rider.state = STATE_IDLE
                fixes.append("rider %s reset to idle" % rider.rider_id)
        for order in self.orders:
            if order.status == "pending" and order.rider_id is not None:
                order.status = "assigned"
                fixes.append("order %s marked assigned" % order.id)
        return fixes

    # ------------------------------------------------------------------
    def save_state(self, path):
        """Persist system parameters, riders and orders to JSON."""
        data = {
            "config": self.config,
            "funds": self.funds,
            "rider_id_counter": globalvar.get_value("rider_id_counter", 0),
            "time": self.time,
            "orders": [o.to_dict() for o in self.orders],
            "riders": [r.to_dict() for r in self.riders],
        }
        with open(path, "w", encoding="utf-8") as fh:
            json.dump(data, fh, indent=2)

    def load_state(self, path):
        """Load state previously written by ``save_state``."""
        from order_model import Order
        with open(path, "r", encoding="utf-8") as fh:
            data = json.load(fh)
        cfg = dict(DEFAULT_CONFIG)
        cfg.update(data.get("config", {}))
        self.config = cfg
        globalvar.set_value("config", cfg)
        globalvar.set_value("funds", int(data.get("funds", 0)))
        globalvar.set_value("rider_id_counter",
                            int(data.get("rider_id_counter", 0)))
        globalvar.set_value("time", int(data.get("time", 0)))
        orders = [Order.from_dict(d) for d in data.get("orders", [])]
        by_id = {o.id: o for o in orders}
        riders = [Rider.from_dict(d, by_id) for d in data.get("riders", [])]
        globalvar.set_value("orders", orders)
        globalvar.set_value("riders", riders)
        globalvar.set_value("running", True)


def init_system(config=None):
    """Initialise the global system state and return the SystemManager."""
    manager = SystemManager(config)
    manager.init()
    return manager


def get_system():
    """Return the active SystemManager, creating one if necessary."""
    manager = globalvar.get_value("system")
    if manager is None:
        manager = SystemManager(globalvar.get_value("config"))
        if globalvar.get_value("riders") is None:
            manager.init()
        else:
            globalvar.set_value("system", manager)
    return manager
