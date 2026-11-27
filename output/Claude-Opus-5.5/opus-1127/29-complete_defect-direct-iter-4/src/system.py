"""System initialisation and the SystemManager core class."""

import json
import logging
import os

import globalvar
from order import find_best_rider_for_order
from order_model import Order
from rider import Rider

logger = logging.getLogger("dispatch.system")

DEFAULT_CONFIG = {
    "initial_funds": 500,
    "recruit_threshold": 300,
    "recruit_cost": 300,
    "rider_speed": 50,
    "spawn_x": 400,
    "spawn_y": 400,
    "order_base_fee": 30,
    "order_fee_per_100": 10,
    "ticks_per_command": 1,
    "max_run_ticks": 10000,
    "save_file": "dispatch_state.json",
}


def load_config(path=None):
    """Load configuration from a JSON file merged over defaults."""
    cfg = dict(DEFAULT_CONFIG)
    if path and os.path.exists(path):
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
            if isinstance(data, dict):
                cfg.update({k: v for k, v in data.items() if k in cfg})
        except (OSError, ValueError) as exc:
            logger.error("Failed to load config %s: %s", path, exc)
    return cfg


def init_system(config=None):
    """Initialise global state and return a SystemManager."""
    globalvar._init()
    cfg = dict(DEFAULT_CONFIG)
    if config:
        cfg.update(config)
    globalvar.set_value("config", cfg)
    globalvar.set_value("riders", [])
    globalvar.set_value("rider_id_counter", 0)
    globalvar.set_value("running", True)
    globalvar.set_value("money", int(cfg["initial_funds"]))
    globalvar.set_value("time", 0)
    globalvar.set_value("orders", [])
    globalvar.set_value("map_size", 800)
    globalvar.set_value("cell_size", 100)
    globalvar.set_value("grid_dim", 8)
    Order.reset_counter(1)
    return SystemManager()


class SystemManager:
    """Manages funds, riders, simulated time and system state."""

    @property
    def config(self):
        return globalvar.get_value("config") or dict(DEFAULT_CONFIG)

    @property
    def funds(self):
        return globalvar.get_value("money", 0)

    @funds.setter
    def funds(self, value):
        globalvar.set_value("money", int(value))

    @property
    def riders(self):
        r = globalvar.get_value("riders")
        if r is None:
            r = []
            globalvar.set_value("riders", r)
        return r

    @property
    def orders(self):
        o = globalvar.get_value("orders")
        if o is None:
            o = []
            globalvar.set_value("orders", o)
        return o

    @property
    def time(self):
        return globalvar.get_value("time", 0)

    @property
    def running(self):
        return globalvar.get_value("running", True)

    @running.setter
    def running(self, value):
        globalvar.set_value("running", bool(value))

    # ------------------------------------------------------------------
    def create_rider(self):
        """Create a rider with the next id and add it to the list."""
        rid = globalvar.get_value("rider_id_counter", 0) + 1
        globalvar.set_value("rider_id_counter", rid)
        rider = Rider(rid)
        self.riders.append(rider)
        logger.info("Rider %s created", rid)
        return rider

    def remove_rider(self, rider_id):
        """Remove an idle rider without orders; return True on success."""
        for r in self.riders:
            if r.rider_id == rider_id and r.state == 0 and not r.orders:
                self.riders.remove(r)
                return True
        return False

    def get_rider(self, rider_id):
        """Return the rider with the given id or None."""
        for r in self.riders:
            if r.rider_id == rider_id:
                return r
        return None

    def auto_recruit(self):
        """Recruit a rider if funds >= threshold; return it or None."""
        cfg = self.config
        if self.funds >= cfg["recruit_threshold"]:
            self.funds = self.funds - cfg["recruit_cost"]
            return self.create_rider()
        return None

    def dispatch_pending(self):
        """Assign any pending, unassigned orders."""
        for o in self.orders:
            if o.status == "pending" and o.rider_id is None:
                best = find_best_rider_for_order(o, self.riders)
                if best is None:
                    break
                o.assign_to(best.rider_id)
                best.orders.append(o)

    def tick(self, n=1):
        """Advance the simulation by ``n`` ticks."""
        for _ in range(max(0, int(n))):
            globalvar.set_value("time", self.time + 1)
            self.dispatch_pending()
            for r in self.riders:
                try:
                    r.move()
                except Exception as exc:  # recovery
                    logger.exception("Rider %s failed: %s", r.rider_id, exc)
                    self.consistency_check()

    def active_orders(self):
        """Return orders not yet completed."""
        return [o for o in self.orders if o.status != "completed"]

    def run_until_complete(self):
        """Tick until all orders are complete; return ticks used."""
        limit = int(self.config.get("max_run_ticks", 10000))
        used = 0
        while self.active_orders() and used < limit:
            if not self.riders:
                break
            self.tick(1)
            used += 1
        return used

    def consistency_check(self):
        """Repair inconsistent state; return a list of fix descriptions."""
        fixes = []
        for r in self.riders:
            before = len(r.orders)
            r.orders[:] = [o for o in r.orders if o.status != "completed"]
            if len(r.orders) != before:
                fixes.append("rider %s: removed completed orders" % r.rider_id)
            if r.state not in (0, 1, 2):
                r.state = 0
                fixes.append("rider %s: invalid state reset" % r.rider_id)
            if r.state != 0 and (r.current_order is None or
                                 r.current_order not in r.orders):
                r.state = 0
                r.current_order = None
                r.path = []
                fixes.append("rider %s: reset to idle" % r.rider_id)
            cx = max(0, min(800, r.x))
            cy = max(0, min(800, r.y))
            if (cx, cy) != (r.x, r.y):
                r.x, r.y = cx, cy
                fixes.append("rider %s: position clamped" % r.rider_id)
        ids = {r.rider_id for r in self.riders}
        for o in self.orders:
            if o.status != "completed" and o.rider_id is not None \
                    and o.rider_id not in ids:
                o.rider_id = None
                o.status = "pending"
                fixes.append("order %s: requeued" % o.id)
        return fixes

    # ------------------------------------------------------------------
    def save_state(self, path=None):
        """Save system state to a JSON file; return the path."""
        path = path or self.config.get("save_file", "dispatch_state.json")
        data = {
            "config": self.config,
            "funds": self.funds,
            "time": self.time,
            "rider_id_counter": globalvar.get_value("rider_id_counter", 0),
            "next_order_id": Order._next_id,
            "orders": [o.to_dict() for o in self.orders],
            "riders": [r.to_dict() for r in self.riders],
        }
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
        return path

    def load_state(self, path=None):
        """Load system state from a JSON file."""
        path = path or self.config.get("save_file", "dispatch_state.json")
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        cfg = dict(DEFAULT_CONFIG)
        cfg.update(data.get("config", {}))
        globalvar.set_value("config", cfg)
        globalvar.set_value("money", int(data.get("funds", 0)))
        globalvar.set_value("time", int(data.get("time", 0)))
        globalvar.set_value("rider_id_counter",
                            int(data.get("rider_id_counter", 0)))
        orders = [Order.from_dict(d) for d in data.get("orders", [])]
        omap = {o.id: o for o in orders}
        riders = [Rider.from_dict(d, omap) for d in data.get("riders", [])]
        globalvar.set_value("orders", orders)
        globalvar.set_value("riders", riders)
        Order.reset_counter(int(data.get("next_order_id",
                                         len(orders) + 1)))
        self.consistency_check()
        return path
