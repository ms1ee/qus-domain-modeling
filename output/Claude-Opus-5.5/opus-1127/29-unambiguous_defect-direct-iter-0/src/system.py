"""System initialisation and resource management."""

import json
import logging
import os

import globalvar
from rider import Rider, STATE_NAMES
from path_planner import planner

logger = logging.getLogger(__name__)

CONFIG_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                           "config.json")

DEFAULT_CONFIG = {
    "initial_funds": 10000,
    "rider_cost": 1000,
    "max_riders": 10,
    "rider_speed": 100,
    "rider_start_x": 400,
    "rider_start_y": 400,
    "data_file": "dispatch_data.json",
}


def load_config(path=None):
    """Load the JSON configuration, merged over the defaults."""
    cfg = dict(DEFAULT_CONFIG)
    path = path or CONFIG_FILE
    try:
        if os.path.isfile(path):
            with open(path, "r", encoding="utf-8") as fh:
                data = json.load(fh)
            if isinstance(data, dict):
                cfg.update(data)
    except (OSError, ValueError) as exc:
        logger.warning("Could not read config %s: %s", path, exc)
    return cfg


def init_system(config=None):
    """Initialise all global system parameters.

    :param config: optional dict overriding configuration values.
    :return: a :class:`SystemManager` bound to the global state.
    """
    cfg = load_config()
    if isinstance(config, dict):
        cfg.update(config)
    globalvar.set_value("config", cfg)
    globalvar.set_value("funds", int(cfg.get("initial_funds", 10000)))
    globalvar.set_value("riders", [])
    globalvar.set_value("rider_id_counter", 0)
    globalvar.set_value("running", True)
    globalvar.set_value("time", 0)
    globalvar.set_value("orders", [])
    globalvar.set_value("pending_orders", [])
    globalvar.set_value("order_counter", 0)
    return SystemManager()


class SystemManager:
    """Manages funds, riders and the overall system state."""

    @property
    def config(self):
        """Current configuration dict."""
        return globalvar.get_value("config") or dict(DEFAULT_CONFIG)

    @property
    def funds(self):
        """Current fund balance."""
        return globalvar.get_value("funds", 0)

    @property
    def riders(self):
        """List of riders (created if missing)."""
        riders = globalvar.get_value("riders")
        if riders is None:
            riders = []
            globalvar.set_value("riders", riders)
        return riders

    @property
    def time(self):
        """Current simulated tick."""
        return globalvar.current_time()

    def get_rider(self, rider_id):
        """Return the rider with ``rider_id`` or None."""
        for r in self.riders:
            if r.rider_id == rider_id:
                return r
        return None

    def can_recruit(self):
        """True if funds and capacity allow recruiting a new rider."""
        cfg = self.config
        return (self.funds >= int(cfg.get("rider_cost", 1000))
                and len(self.riders) < int(cfg.get("max_riders", 10)))

    def needs_rider(self):
        """True if no idle rider is available."""
        return not any(r.is_idle() for r in self.riders)

    def recruit_rider(self):
        """Recruit a new rider if allowed. Returns the rider or None."""
        if not self.can_recruit():
            return None
        counter = (globalvar.get_value("rider_id_counter") or 0) + 1
        globalvar.set_value("rider_id_counter", counter)
        rider = Rider(counter)
        globalvar.set_value("funds",
                            self.funds - int(self.config.get("rider_cost",
                                                             1000)))
        self.riders.append(rider)
        logger.info("Recruited rider %s", counter)
        return rider

    def advance_tick(self):
        """Advance simulated time by one tick and move all riders."""
        globalvar.set_value("time", self.time + 1)
        for rider in list(self.riders):
            rider.move()
        self.check_consistency()
        return self.time

    def check_consistency(self):
        """Verify and repair system state. Returns a list of issues fixed."""
        issues = []
        seen = set()
        for rider in self.riders:
            if rider.rider_id in seen:
                issues.append("duplicate rider id %s" % rider.rider_id)
            seen.add(rider.rider_id)
            if rider.state not in STATE_NAMES:
                issues.append("rider %s invalid state" % rider.rider_id)
                rider.state = 0
                rider.current_order = None
                rider.target = None
                rider.path = []
            if not planner.is_on_road(rider.x, rider.y):
                issues.append("rider %s off road" % rider.rider_id)
                rider.x, rider.y = planner.snap_to_road(rider.x, rider.y)
                rider.target = None
                rider.path = []
        counter = globalvar.get_value("rider_id_counter") or 0
        if seen and max(seen) > counter:
            globalvar.set_value("rider_id_counter", max(seen))
        for issue in issues:
            logger.warning("Consistency: %s", issue)
        return issues

    def save_state(self, path=None):
        """Persist configuration, riders and order history to JSON."""
        path = path or self.config.get("data_file", "dispatch_data.json")
        data = {
            "config": self.config,
            "funds": self.funds,
            "time": self.time,
            "rider_id_counter": globalvar.get_value("rider_id_counter"),
            "riders": [r.to_dict() for r in self.riders],
            "orders": [o.to_dict() for o in
                       (globalvar.get_value("orders") or [])],
        }
        try:
            with open(path, "w", encoding="utf-8") as fh:
                json.dump(data, fh, indent=2)
            return path
        except OSError as exc:
            logger.error("Could not save state to %s: %s", path, exc)
            return None
