"""System initialisation and the SystemManager core class."""

import json
import logging

import globalvar
import order_model
from config import (DEFAULTS, DEFAULT_SAVE_FILE)
from order_model import Order, STATUS_PENDING
from rider import Rider

logger = logging.getLogger(__name__)


def init_system(config=None):
    """Initialise the global system state.

    Sets funds (1000), an empty rider list, rider ID counter (0), running
    state (True), simulated time (0) and an empty order list.
    """
    cfg = dict(DEFAULTS)
    if config:
        cfg.update(config)
    globalvar._init()
    globalvar.set_value("funds", int(cfg["initial_funds"]))
    globalvar.set_value("riders", [])
    globalvar.set_value("rider_id_counter", 0)
    globalvar.set_value("running", True)
    globalvar.set_value("time", 0)
    globalvar.set_value("orders", [])
    globalvar.set_value("config", cfg)
    globalvar.set_value("map_size", 800)
    globalvar.set_value("cell_size", 100)


class SystemManager:
    """Manages funds, riders, simulated time and system state."""

    def __init__(self, config=None, initialise=True):
        if initialise or globalvar.get_value("riders") is None:
            init_system(config)

    # ------------------------------------------------------------ properties
    @property
    def config(self):
        return globalvar.get_value("config") or dict(DEFAULTS)

    @property
    def funds(self):
        return globalvar.get_value("funds", 0)

    @funds.setter
    def funds(self, value):
        globalvar.set_value("funds", int(value))

    @property
    def riders(self):
        riders = globalvar.get_value("riders")
        if riders is None:
            riders = []
            globalvar.set_value("riders", riders)
        return riders

    @property
    def time(self):
        return globalvar.get_value("time", 0)

    @property
    def running(self):
        return bool(globalvar.get_value("running", False))

    def stop(self):
        """Stop the main loop."""
        globalvar.set_value("running", False)

    # --------------------------------------------------------------- riders
    def recruit_rider(self):
        """Create a new rider, deducting the recruitment cost."""
        counter = globalvar.get_value("rider_id_counter", 0) + 1
        globalvar.set_value("rider_id_counter", counter)
        start = self.config.get("rider_start", [400, 400])
        rider = Rider(counter, start[0], start[1],
                      self.config.get("rider_speed"))
        self.riders.append(rider)
        self.funds = self.funds - int(self.config["rider_cost"])
        logger.info("Recruited rider %s; funds now %s", counter, self.funds)
        return rider

    def get_rider(self, rider_id):
        """Return rider by ID or None."""
        for r in self.riders:
            if r.rider_id == rider_id:
                return r
        return None

    def idle_rider_count(self):
        """Number of riders with no outstanding orders."""
        return sum(1 for r in self.riders if r.is_idle())

    def pending_order_count(self):
        """Number of orders not yet assigned to a rider."""
        orders = globalvar.get_value("orders") or []
        return sum(1 for o in orders if o.status == STATUS_PENDING)

    def auto_recruit(self):
        """Recruit riders while funds ≥ threshold and pending > idle.

        Returns the list of newly recruited riders.
        """
        new = []
        threshold = int(self.config["recruit_threshold"])
        while (self.funds >= threshold
               and self.pending_order_count() > self.idle_rider_count()):
            new.append(self.recruit_rider())
        return new

    # ----------------------------------------------------------- simulation
    def tick(self):
        """Advance simulated time by one tick and move all riders."""
        globalvar.set_value("time", self.time + 1)
        for rider in list(self.riders):
            try:
                rider.move()
            except Exception as exc:  # recover from a faulty rider
                logger.exception("Rider %s failed to move: %s",
                                 rider.rider_id, exc)
                rider.current_order = None
                rider.path = []
                rider.state = 0

    def all_delivered(self):
        """True if every order has been completed."""
        orders = globalvar.get_value("orders") or []
        return all(o.is_completed() for o in orders)

    def check_consistency(self):
        """Fix and report inconsistencies. Returns list of messages."""
        issues = []
        ids = set()
        for r in self.riders:
            if r.rider_id in ids:
                issues.append("Duplicate rider id %s" % r.rider_id)
            ids.add(r.rider_id)
            if r.state not in (0, 1, 2):
                issues.append("Rider %s invalid state %s; reset to idle"
                              % (r.rider_id, r.state))
                r.state = 0
                r.current_order = None
            if r.state == 0 and r.current_order is not None:
                r.current_order = None
        return issues

    # ---------------------------------------------------------- persistence
    def save(self, path=DEFAULT_SAVE_FILE):
        """Save system state to a JSON file."""
        orders = globalvar.get_value("orders") or []
        data = {
            "funds": self.funds,
            "rider_id_counter": globalvar.get_value("rider_id_counter", 0),
            "time": self.time,
            "config": self.config,
            "orders": [o.to_dict() for o in orders],
            "riders": [r.to_dict() for r in self.riders],
        }
        with open(path, "w", encoding="utf-8") as fh:
            json.dump(data, fh, indent=2)
        return path

    def load(self, path=DEFAULT_SAVE_FILE):
        """Load system state from a JSON file."""
        with open(path, "r", encoding="utf-8") as fh:
            data = json.load(fh)
        init_system(data.get("config"))
        globalvar.set_value("funds", int(data.get("funds", 0)))
        globalvar.set_value("rider_id_counter",
                            int(data.get("rider_id_counter", 0)))
        globalvar.set_value("time", int(data.get("time", 0)))
        orders = [Order.from_dict(d) for d in data.get("orders", [])]
        globalvar.set_value("orders", orders)
        by_id = {o.id: o for o in orders}
        max_id = max(by_id) if by_id else 0
        order_model.reset_order_ids(max_id + 1)
        riders = [Rider.from_dict(d, by_id) for d in data.get("riders", [])]
        globalvar.set_value("riders", riders)
        return path
