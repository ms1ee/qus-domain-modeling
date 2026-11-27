"""System manager: funds, riders, simulated time and persistence."""

import json
import logging

import config
import globalvar
from order import OrderManager
from order_model import Order
from rider import Rider, IDLE, PICKING_UP, DELIVERING

logger = logging.getLogger(__name__)


class SystemManager:
    """Core class managing funds, riders, time and system state.

    All state lives in :mod:`globalvar` so that other modules can access it.
    """

    def __init__(self):
        self.order_manager = OrderManager(self)

    # ------------------------------------------------------------ properties
    @property
    def funds(self):
        """Current system funds."""
        return globalvar.get_value("funds", 0)

    @funds.setter
    def funds(self, value):
        globalvar.set_value("funds", int(value))

    @property
    def riders(self):
        """List of all riders."""
        riders = globalvar.get_value("riders")
        if riders is None:
            riders = []
            globalvar.set_value("riders", riders)
        return riders

    @property
    def time(self):
        """Current simulated tick."""
        return globalvar.get_value("time", 0)

    @property
    def running(self):
        """Main loop running flag."""
        return bool(globalvar.get_value("running", False))

    def stop(self):
        """Stop the main loop."""
        globalvar.set_value("running", False)

    # ---------------------------------------------------------------- riders
    def idle_riders(self):
        """Riders that are idle with no queued orders."""
        return [r for r in self.riders if r.is_idle()]

    def get_rider(self, rider_id):
        """Return the rider with ``rider_id`` or None."""
        for r in self.riders:
            if r.rider_id == rider_id:
                return r
        return None

    def recruit_rider(self):
        """Recruit a rider if funds allow; returns the rider or None."""
        cost = int(config.get("rider_cost"))
        if self.funds < cost:
            return None
        self.funds = self.funds - cost
        counter = globalvar.get_value("rider_id_counter", 0) + 1
        globalvar.set_value("rider_id_counter", counter)
        rider = Rider(counter)
        self.riders.append(rider)
        logger.info("Recruited rider %d, funds now %d", counter, self.funds)
        return rider

    def auto_recruit(self):
        """Recruit riders while funds >= cost and pending > idle riders."""
        new = []
        cost = int(config.get("rider_cost"))
        while (self.funds >= cost and
               len(self.order_manager.pending_orders()) > len(self.idle_riders())):
            rider = self.recruit_rider()
            if rider is None:
                break
            new.append(rider)
        return new

    # ------------------------------------------------------------ simulation
    def tick(self, n=1):
        """Advance the simulation ``n`` ticks; returns completed orders."""
        completed = []
        for _ in range(max(0, int(n))):
            globalvar.set_value("time", self.time + 1)
            self.auto_recruit()
            self.order_manager.assign_pending()
            for rider in list(self.riders):
                before = set(o.id for o in rider.orders)
                try:
                    rider.move()
                except Exception as exc:  # error recovery
                    logger.exception("Rider %s failed to move: %s",
                                     rider.rider_id, exc)
                    rider.state = IDLE
                after = set(o.id for o in rider.orders)
                for oid in before - after:
                    for o in self.order_manager.all_orders():
                        if o.id == oid and o.status == "completed":
                            completed.append(o)
            self.check_consistency()
        return completed

    def has_active_work(self):
        """True when any order is not yet completed."""
        return any(o.status != "completed"
                   for o in self.order_manager.all_orders())

    def run_until_idle(self, limit=None):
        """Tick until all orders are completed (or ``limit`` ticks)."""
        limit = int(limit or config.get("max_run_ticks"))
        ticks = 0
        while self.has_active_work() and ticks < limit:
            if not self.riders and self.funds < int(config.get("rider_cost")):
                break
            self.tick(1)
            ticks += 1
        return ticks

    def check_consistency(self):
        """Repair inconsistent state; returns a list of fixes applied."""
        fixes = []
        size = int(config.get("map_size"))
        rider_ids = {r.rider_id for r in self.riders}
        for r in self.riders:
            if r.state not in (IDLE, PICKING_UP, DELIVERING):
                r.state = IDLE
                fixes.append("rider %s invalid state reset" % r.rider_id)
            if r.state != IDLE and not r.orders:
                r.state = IDLE
                fixes.append("rider %s busy without orders reset" % r.rider_id)
            cx = max(0, min(size, r.x))
            cy = max(0, min(size, r.y))
            if (cx, cy) != (r.x, r.y):
                r.x, r.y = cx, cy
                fixes.append("rider %s position clamped" % r.rider_id)
        held = {id(o) for r in self.riders for o in r.orders}
        for o in self.order_manager.all_orders():
            if o.status in ("assigned", "picking_up", "delivering"):
                if o.rider_id not in rider_ids or id(o) not in held:
                    o.status = "pending"
                    o.rider_id = None
                    fixes.append("order %d returned to pending" % o.id)
        for fix in fixes:
            logger.warning("Consistency fix: %s", fix)
        return fixes

    # ----------------------------------------------------------- persistence
    def to_dict(self):
        """Serialise the whole system state."""
        return {
            "system": config.get_all(),
            "funds": self.funds,
            "time": self.time,
            "rider_id_counter": globalvar.get_value("rider_id_counter", 0),
            "riders": [r.to_dict() for r in self.riders],
            "orders": [o.to_dict() for o in self.order_manager.all_orders()],
        }

    def save(self, path=None):
        """Save the state to a JSON file; returns the path used."""
        path = path or config.get("state_file")
        with open(path, "w", encoding="utf-8") as fh:
            json.dump(self.to_dict(), fh, indent=2)
        return path

    def load(self, path=None):
        """Load state from a JSON file written by :meth:`save`."""
        path = path or config.get("state_file")
        with open(path, "r", encoding="utf-8") as fh:
            data = json.load(fh)
        if isinstance(data.get("system"), dict):
            config.set_active(data["system"])
        orders = [Order.from_dict(d) for d in data.get("orders", [])]
        by_id = {o.id: o for o in orders}
        riders = [Rider.from_dict(d, by_id) for d in data.get("riders", [])]
        globalvar.set_value("funds", int(data.get("funds", self.funds)))
        globalvar.set_value("time", int(data.get("time", 0)))
        globalvar.set_value("rider_id_counter",
                            int(data.get("rider_id_counter", len(riders))))
        globalvar.set_value("orders", orders)
        globalvar.set_value("riders", riders)
        Order.reset_counter(max(by_id) + 1 if by_id else 1)
        self.check_consistency()
        return path


def init_system(config_path=None):
    """Initialise global state and return a :class:`SystemManager`.

    Funds = 1000, riders = [], rider id counter = 0, running = True,
    time = 0, orders = [].
    """
    cfg = config.load_config(config_path) if config_path else None
    config.set_active(cfg)
    globalvar._init()
    globalvar.set_value("funds", int(config.get("initial_funds")))
    globalvar.set_value("riders", [])
    globalvar.set_value("rider_id_counter", 0)
    globalvar.set_value("running", True)
    globalvar.set_value("time", 0)
    globalvar.set_value("orders", [])
    Order.reset_counter(1)
    manager = SystemManager()
    globalvar.set_value("system", manager)
    return manager
