"""System initialisation and the SystemManager core class."""

import json
import logging
import os

import globalvar
from config import load_config, BASE_DIR
from rider import Rider

logger = logging.getLogger(__name__)


def init_system(config_path=None):
    """Initialise all global state and return a SystemManager."""
    globalvar._init()
    cfg = load_config(config_path)
    globalvar.set_value("config", cfg)
    globalvar.set_value("funds", int(cfg["initial_funds"]))
    globalvar.set_value("riders", [])
    globalvar.set_value("rider_id_counter", 0)
    globalvar.set_value("running", True)
    globalvar.set_value("time", 0)
    globalvar.set_value("orders", [])
    globalvar.set_value("order_id_counter", 0)
    manager = SystemManager()
    globalvar.set_value("system_manager", manager)
    return manager


class SystemManager:
    """Manages funds, riders, simulated time and system state."""

    @property
    def config(self):
        return globalvar.get_value("config") or {}

    @property
    def funds(self):
        return globalvar.get_value("funds", 0)

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

    def adjust_funds(self, delta):
        """Add ``delta`` (may be negative) to the funds."""
        globalvar.set_value("funds", int(self.funds) + int(delta))

    def idle_riders(self):
        """Riders that are idle and have no queued orders."""
        return [r for r in self.riders if r.state == 0 and not r.orders]

    def can_recruit(self):
        """True if funds and rider limit allow recruiting."""
        cfg = self.config
        return (self.funds >= cfg.get("rider_cost", 1000)
                and len(self.riders) < cfg.get("max_riders", 10))

    def recruit_rider(self):
        """Recruit a rider unconditionally if allowed by funds; return it."""
        if not self.can_recruit():
            return None
        counter = (globalvar.get_value("rider_id_counter", 0) or 0) + 1
        globalvar.set_value("rider_id_counter", counter)
        rider = Rider(counter)
        self.riders.append(rider)
        self.adjust_funds(-self.config.get("rider_cost", 1000))
        logger.info("Recruited rider %d", counter)
        return rider

    def auto_recruit(self):
        """Recruit a rider if none is idle and funds allow it."""
        if not self.idle_riders() and self.can_recruit():
            return self.recruit_rider()
        return None

    def tick(self, n=1):
        """Advance the simulation ``n`` ticks."""
        for _ in range(max(0, int(n))):
            globalvar.set_value("time", self.time + 1)
            for rider in list(self.riders):
                try:
                    rider.move()
                except Exception:  # pragma: no cover - recovery path
                    logger.exception("Rider %s failed to move; resetting", rider.rider_id)
                    rider.reset()

    def all_orders_completed(self):
        orders = globalvar.get_value("orders") or []
        return all(o.status == "completed" for o in orders)

    def run_until_idle(self, max_ticks=10000):
        """Tick until every order is delivered; return ticks used."""
        used = 0
        while not (self.all_orders_completed() and all(r.state == 0 for r in self.riders)):
            if used >= max_ticks:
                break
            self.tick()
            used += 1
        return used

    def check_consistency(self):
        """Detect and repair inconsistent state; return list of issues."""
        issues = []
        if not isinstance(globalvar.get_value("funds"), int):
            issues.append("funds reset")
            globalvar.set_value("funds", 0)
        if not isinstance(globalvar.get_value("time"), int):
            issues.append("time reset")
            globalvar.set_value("time", 0)
        if not isinstance(globalvar.get_value("orders"), list):
            issues.append("orders reset")
            globalvar.set_value("orders", [])
        seen = set()
        for rider in self.riders:
            if rider.rider_id in seen:
                issues.append("duplicate rider id %d" % rider.rider_id)
            seen.add(rider.rider_id)
            if rider.state not in (0, 1, 2) or (rider.state != 0 and rider.current_order is None
                                                 and not rider.orders):
                issues.append("rider %d state reset" % rider.rider_id)
                rider.reset()
            if not (0 <= rider.x <= 800 and 0 <= rider.y <= 800):
                issues.append("rider %d position reset" % rider.rider_id)
                rider.reset()
        return issues

    def stop(self):
        globalvar.set_value("running", False)

    def save_state(self, path=None):
        """Persist configuration, riders and order history as JSON."""
        path = path or os.path.join(BASE_DIR, self.config.get("state_file", "dispatch_state.json"))
        data = {
            "config": self.config,
            "funds": self.funds,
            "time": self.time,
            "rider_id_counter": globalvar.get_value("rider_id_counter", 0),
            "riders": [r.to_dict() for r in self.riders],
            "orders": [o.to_dict() for o in (globalvar.get_value("orders") or [])],
        }
        try:
            with open(path, "w", encoding="utf-8") as fh:
                json.dump(data, fh, indent=2)
            return path
        except OSError as exc:
            logger.warning("Could not save state: %s", exc)
            return None
