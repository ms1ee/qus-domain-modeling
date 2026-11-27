"""System initialisation and the SystemManager core class."""

import json
import logging
import os

import globalvar as gv
from order_model import Order
from rider import Rider, STATE_IDLE

logger = logging.getLogger("dispatch")

DEFAULT_CONFIG = {
    "initial_funds": 1000,
    "rider_cost": 300,
    "rider_speed": 10,
    "spawn_x": 435,
    "spawn_y": 385,
}


def init_system(config=None):
    """Initialise all global system parameters.

    funds=1000, riders=[], rider_id_counter=0, running=True, plus the
    order list, order counter and simulated time.
    """
    cfg = dict(DEFAULT_CONFIG)
    if config:
        cfg.update(config)
    gv.set_value("config", cfg)
    gv.set_value("funds", int(cfg["initial_funds"]))
    gv.set_value("riders", [])
    gv.set_value("rider_id_counter", 0)
    gv.set_value("running", True)
    gv.set_value("orders", [])
    gv.set_value("order_id_counter", 0)
    gv.set_value("time", 0)


def load_config(path):
    """Load a JSON config file; returns {} if missing or invalid."""
    if not path or not os.path.exists(path):
        return {}
    try:
        with open(path, "r", encoding="utf-8") as fh:
            data = json.load(fh)
        return {k: data[k] for k in DEFAULT_CONFIG if k in data}
    except (OSError, ValueError) as exc:
        logger.warning("Could not load config %s: %s", path, exc)
        return {}


class SystemManager:
    """Manages funds, riders, simulated time and system state."""

    @property
    def funds(self):
        """Current fund balance."""
        return gv.get_value("funds", 0)

    @property
    def riders(self):
        """List of riders."""
        riders = gv.get_value("riders")
        if riders is None:
            riders = []
            gv.set_value("riders", riders)
        return riders

    @property
    def time(self):
        """Current simulated tick."""
        return gv.get_value("time", 0)

    def create_rider(self):
        """Create a rider, deducting the recruitment cost."""
        cfg = gv.get_value("config") or DEFAULT_CONFIG
        counter = (gv.get_value("rider_id_counter", 0) or 0) + 1
        gv.set_value("rider_id_counter", counter)
        rider = Rider(counter)
        self.riders.append(rider)
        gv.set_value("funds", self.funds - int(cfg.get("rider_cost", 300)))
        logger.info("Recruited rider %d", counter)
        return rider

    def maybe_recruit(self):
        """Recruit a rider if funds >= cost and pending > idle riders.

        Returns the new rider or None.
        """
        cfg = gv.get_value("config") or DEFAULT_CONFIG
        cost = int(cfg.get("rider_cost", 300))
        orders = gv.get_value("orders") or []
        pending = sum(1 for o in orders if o.status == "pending")
        idle = sum(1 for r in self.riders
                   if r.state == STATE_IDLE and not r.orders)
        if self.funds >= cost and pending > idle:
            return self.create_rider()
        return None

    def tick(self, order_manager=None):
        """Advance the simulation by one tick."""
        gv.set_value("time", self.time + 1)
        if order_manager is not None:
            order_manager.assign_pending()
        for rider in self.riders:
            rider.move()

    def all_idle(self):
        """True if no orders are outstanding."""
        orders = gv.get_value("orders") or []
        return all(o.status == "completed" for o in orders)

    def consistency_check(self):
        """Repair inconsistent state; returns list of fixes applied."""
        fixes = []
        for rider in self.riders:
            rider.x = max(0, min(800, int(rider.x)))
            rider.y = max(0, min(800, int(rider.y)))
            if rider.state not in (0, 1, 2):
                rider.state = STATE_IDLE
                fixes.append("rider %s invalid state reset" % rider.rider_id)
            if rider.current_order is None and rider.state != STATE_IDLE:
                rider.state = STATE_IDLE
                rider.path = []
                fixes.append("rider %s state reset to idle" % rider.rider_id)
            if (rider.current_order is not None
                    and rider.current_order.status == "completed"):
                rider.current_order = None
                rider.state = STATE_IDLE
                rider.path = []
                fixes.append("rider %s cleared finished order" % rider.rider_id)
            before = len(rider.orders)
            rider.orders = [o for o in rider.orders if o.status != "completed"]
            if len(rider.orders) != before:
                fixes.append("rider %s removed completed orders" % rider.rider_id)
        if gv.get_value("running") is None:
            gv.set_value("running", True)
        for fix in fixes:
            logger.warning("Consistency fix: %s", fix)
        return fixes

    # ---------------------------------------------------------- persistence
    def save_state(self, path):
        """Save config, riders and order history to a JSON file."""
        data = {
            "config": gv.get_value("config"),
            "funds": self.funds,
            "rider_id_counter": gv.get_value("rider_id_counter", 0),
            "order_id_counter": gv.get_value("order_id_counter", 0),
            "time": self.time,
            "riders": [r.to_dict() for r in self.riders],
            "orders": [o.to_dict() for o in (gv.get_value("orders") or [])],
        }
        with open(path, "w", encoding="utf-8") as fh:
            json.dump(data, fh, indent=2)

    def load_state(self, path):
        """Load state saved by :meth:`save_state`."""
        with open(path, "r", encoding="utf-8") as fh:
            data = json.load(fh)
        cfg = dict(DEFAULT_CONFIG)
        cfg.update(data.get("config") or {})
        orders = [Order.from_dict(d) for d in data.get("orders", [])]
        by_id = {o.id: o for o in orders}
        riders = [Rider.from_dict(d, by_id) for d in data.get("riders", [])]
        gv.set_value("config", cfg)
        gv.set_value("funds", int(data.get("funds", cfg["initial_funds"])))
        gv.set_value("rider_id_counter", int(data.get("rider_id_counter", 0)))
        gv.set_value("order_id_counter", int(data.get("order_id_counter", 0)))
        gv.set_value("time", int(data.get("time", 0)))
        gv.set_value("orders", orders)
        gv.set_value("riders", riders)
        gv.set_value("running", True)
        self.consistency_check()
