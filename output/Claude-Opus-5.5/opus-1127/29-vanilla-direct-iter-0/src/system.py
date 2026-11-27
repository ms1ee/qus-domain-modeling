"""System initialization and resource management."""

import json
import logging
import os

import globalvar
from rider import Rider
from order_model import Order

INITIAL_FUNDS = 1000
RIDER_COST = 300
DEFAULT_STATE_FILE = "dispatch_state.json"

logger = logging.getLogger(__name__)


def init_system(initial_funds=INITIAL_FUNDS):
    """Initialize all global state with default values."""
    globalvar._init()
    globalvar.set_value("funds", initial_funds)
    globalvar.set_value("riders", [])
    globalvar.set_value("rider_id_counter", 0)
    globalvar.set_value("running", True)
    globalvar.set_value("orders", [])
    globalvar.set_value("pending_orders", [])
    globalvar.set_value("time", 0)
    globalvar.set_value("order_id_counter", 0)


class SystemManager:
    """Manages funds, riders, simulated time and system state."""

    def __init__(self, initial_funds=INITIAL_FUNDS, reset=True):
        if reset or globalvar.get_value("riders") is None:
            init_system(initial_funds)

    # properties ---------------------------------------------------------
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
        return globalvar.get_value("running", True)

    def stop(self):
        """Stop the main loop."""
        globalvar.set_value("running", False)

    # riders -------------------------------------------------------------
    def idle_riders(self):
        """List of riders without any work."""
        return [r for r in self.riders if r.is_idle()]

    def recruit_rider(self):
        """Create a new rider, paying the recruitment cost."""
        counter = globalvar.get_value("rider_id_counter", 0) + 1
        globalvar.set_value("rider_id_counter", counter)
        rider = Rider(counter)
        self.riders.append(rider)
        globalvar.set_value("funds", self.funds - RIDER_COST)
        logger.info("Recruited rider %s", counter)
        return rider

    def auto_recruit(self):
        """Recruit riders while funds >= cost and pending > idle riders.

        Returns the list of newly created riders.
        """
        new = []
        pending = globalvar.get_value("pending_orders", [])
        while self.funds >= RIDER_COST and len(pending) > len(self.idle_riders()):
            new.append(self.recruit_rider())
        return new

    def get_rider(self, rider_id):
        """Find a rider by id."""
        for r in self.riders:
            if r.rider_id == rider_id:
                return r
        return None

    # simulation ---------------------------------------------------------
    def tick(self, order_manager=None):
        """Advance the simulation by one tick."""
        globalvar.set_value("time", self.time + 1)
        for rider in list(self.riders):
            try:
                rider.move()
            except Exception:  # pragma: no cover - recovery path
                logger.exception("Error moving rider %s; resetting", rider.rider_id)
                rider.state = 0
        if order_manager is not None:
            self.auto_recruit()
            order_manager.dispatch_pending()

    def check_consistency(self):
        """Repair inconsistent rider states; returns list of fixes."""
        fixes = []
        for r in self.riders:
            if r.state != 0 and not r.orders:
                r.state = 0
                fixes.append("rider %s reset to idle" % r.rider_id)
            if r.state not in (0, 1, 2):
                r.state = 0
                fixes.append("rider %s invalid state reset" % r.rider_id)
        return fixes

    # persistence --------------------------------------------------------
    def save(self, path=DEFAULT_STATE_FILE):
        """Save the full system state to a JSON file."""
        data = {
            "funds": self.funds,
            "time": self.time,
            "rider_id_counter": globalvar.get_value("rider_id_counter", 0),
            "order_id_counter": globalvar.get_value("order_id_counter", 0),
            "riders": [r.to_dict() for r in self.riders],
            "orders": [o.to_dict() for o in globalvar.get_value("orders", [])],
            "pending_orders": [o.id for o in globalvar.get_value("pending_orders", [])],
        }
        with open(path, "w", encoding="utf-8") as fh:
            json.dump(data, fh, indent=2)
        return path

    def load(self, path=DEFAULT_STATE_FILE):
        """Load system state from a JSON file."""
        if not os.path.exists(path):
            raise FileNotFoundError(path)
        with open(path, "r", encoding="utf-8") as fh:
            data = json.load(fh)
        init_system(data.get("funds", INITIAL_FUNDS))
        globalvar.set_value("time", data.get("time", 0))
        globalvar.set_value("rider_id_counter", data.get("rider_id_counter", 0))
        globalvar.set_value("order_id_counter", data.get("order_id_counter", 0))
        orders = [Order.from_dict(d) for d in data.get("orders", [])]
        by_id = {o.id: o for o in orders}
        globalvar.set_value("orders", orders)
        globalvar.set_value("pending_orders",
                            [by_id[i] for i in data.get("pending_orders", []) if i in by_id])
        riders = []
        for rd in data.get("riders", []):
            r = Rider(rd["rider_id"], rd["x"], rd["y"], rd.get("speed", 10))
            r.state = rd.get("state", 0)
            r.special_case = rd.get("special_case", False)
            r.orders = [by_id[i] for i in rd.get("orders", []) if i in by_id]
            r.log = rd.get("log", r.log)
            riders.append(r)
        globalvar.set_value("riders", riders)
        self.check_consistency()
        return path


def load_config(path):
    """Load a JSON configuration file of system parameters."""
    with open(path, "r", encoding="utf-8") as fh:
        return json.load(fh)
